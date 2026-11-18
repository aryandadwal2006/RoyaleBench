"""Match-level train/validation/test trajectory export."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MatchSource:
    path: Path
    match_id: str
    seed: int
    manifest: dict[str, Any]
    result: dict[str, Any]


class _GzipJsonlWriter:
    def __init__(self, path: Path) -> None:
        self.raw = path.open("wb")
        self.compressed = gzip.GzipFile(fileobj=self.raw, mode="wb", mtime=0)
        self.text = io.TextIOWrapper(self.compressed, encoding="utf-8", newline="\\n")

    def write(self, record: dict[str, Any]) -> None:
        self.text.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
        self.text.write("\n")

    def close(self) -> None:
        self.text.close()
        self.raw.close()


def _discover_matches(matches_root: Path) -> list[MatchSource]:
    sources: list[MatchSource] = []
    seen_ids: set[str] = set()
    for result_path in sorted(matches_root.rglob("result.json")):
        match_dir = result_path.parent
        trajectory = match_dir / "trajectory.jsonl.gz"
        manifest_path = match_dir / "manifest.json"
        if not trajectory.is_file() or not manifest_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "completed" or result.get("outcome") not in {
            "seat0_win",
            "seat1_win",
            "draw",
        }:
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        match_id = str(manifest.get("match_id", result.get("match_id", "")))
        if not match_id:
            raise ValueError(f"missing match_id in {manifest_path}")
        if match_id in seen_ids:
            raise ValueError(f"duplicate match_id in dataset source: {match_id}")
        seen_ids.add(match_id)
        sources.append(
            MatchSource(
                path=match_dir,
                match_id=match_id,
                seed=int(manifest["seed"]),
                manifest=manifest,
                result=result,
            )
        )
    return sources


def _assign_splits(
    sources: list[MatchSource],
    *,
    seed: int,
    validation_fraction: float,
    test_fraction: float,
) -> dict[str, list[MatchSource]]:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between zero and one")
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between zero and one")
    if validation_fraction + test_fraction >= 1.0:
        raise ValueError("validation and test fractions must sum to less than one")

    # All side-swapped matches and all agent pairings with the same deterministic
    # simulator seed stay in one split. Splitting by match_id alone would leak a
    # paired seed: the training split could contain one side assignment while the
    # test split contains its exact mirrored counterpart.
    by_seed: dict[int, list[MatchSource]] = defaultdict(list)
    for source in sources:
        by_seed[source.seed].append(source)
    seed_groups = sorted(
        by_seed,
        key=lambda group_seed: hashlib.sha256(f"{seed}:{group_seed}".encode()).hexdigest(),
    )
    if len(seed_groups) < 3:
        raise ValueError(
            "at least three distinct simulator seed groups are required to create "
            "non-empty train, validation and test splits; increase the tournament seed count"
        )

    validation_count = max(1, round(len(seed_groups) * validation_fraction))
    test_count = max(1, round(len(seed_groups) * test_fraction))
    train_count = len(seed_groups) - validation_count - test_count
    if train_count < 1:
        raise ValueError("not enough distinct seed groups for the requested split fractions")

    split_seeds = {
        "train": seed_groups[:train_count],
        "validation": seed_groups[train_count : train_count + validation_count],
        "test": seed_groups[train_count + validation_count :],
    }
    return {
        split: [
            source
            for group_seed in group_seeds
            for source in sorted(by_seed[group_seed], key=lambda item: item.match_id)
        ]
        for split, group_seeds in split_seeds.items()
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_dataset(
    matches_root: str | Path,
    output_dir: str | Path,
    *,
    split_seed: int = 20261118,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
) -> dict[str, Any]:
    """Export complete match trajectories into deterministic compressed JSONL splits.

    Splits are assigned by whole match, never by individual state transition, which prevents
    frames from the same battle from leaking across training and held-out data.
    """
    source_root = Path(matches_root)
    destination = Path(output_dir)
    if not source_root.is_dir():
        raise FileNotFoundError(f"matches root does not exist: {source_root}")

    sources = _discover_matches(source_root)
    if not sources:
        raise ValueError(f"no completed match trajectories found under {source_root}")

    engine_fingerprints = {
        json.dumps(source.manifest.get("engine", {}), sort_keys=True) for source in sources
    }
    if len(engine_fingerprints) != 1:
        raise ValueError(
            "source matches use different engine/data fingerprints; build separate datasets"
        )

    split_sources = _assign_splits(
        sources,
        seed=split_seed,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
    )
    destination.mkdir(parents=True, exist_ok=True)
    paths = {split: destination / f"{split}.jsonl.gz" for split in split_sources}
    manifest_path = destination / "dataset_manifest.json"
    existing_outputs = [path for path in (*paths.values(), manifest_path) if path.exists()]
    if existing_outputs:
        names = ", ".join(str(path) for path in existing_outputs)
        raise FileExistsError(
            f"dataset output already exists ({names}); choose a new output directory"
        )
    writers = {split: _GzipJsonlWriter(path) for split, path in paths.items()}
    transition_counts = {split: 0 for split in split_sources}
    transition_matches = {split: [] for split in split_sources}

    try:
        for split, match_group in split_sources.items():
            for source in match_group:
                trajectory_path = source.path / "trajectory.jsonl.gz"
                match_transitions = 0
                with gzip.open(trajectory_path, "rt", encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if not line.strip():
                            continue
                        transition = json.loads(line)
                        observation = transition.get("observation")
                        next_observation = transition.get("next_observation")
                        response = transition.get("response")
                        if not isinstance(observation, dict) or not isinstance(
                            next_observation, dict
                        ):
                            raise ValueError(
                                f"invalid transition at {trajectory_path}:{line_number}"
                            )
                        if not isinstance(response, dict) or not isinstance(
                            response.get("action"), dict
                        ):
                            raise ValueError(
                                f"missing ActionV1 at {trajectory_path}:{line_number}"
                            )
                        writers[split].write(
                            {
                                "schema": "royalebench.transition.v1",
                                "match_id": source.match_id,
                                "seed": source.seed,
                                "seat": int(transition["seat"]),
                                "decision_id": int(observation["decision_id"]),
                                "engine_tick": int(transition["engine_tick"]),
                                "action": response["action"],
                                "observation": observation,
                                "next_observation": next_observation,
                                "observation_hash": transition["observation_hash"],
                                "next_observation_hash": transition[
                                    "next_observation_hash"
                                ],
                                "match_outcome": source.result["outcome"],
                            }
                        )
                        match_transitions += 1
                if match_transitions == 0:
                    raise ValueError(f"completed match has no transitions: {source.match_id}")
                transition_counts[split] += match_transitions
                transition_matches[split].append(source.match_id)
    finally:
        for writer in writers.values():
            writer.close()

    all_ids = [
        match_id for match_ids in transition_matches.values() for match_id in match_ids
    ]
    if len(all_ids) != len(set(all_ids)):
        raise RuntimeError("match-level split leakage detected")

    first_engine = sources[0].manifest.get("engine", {})
    manifest = {
        "schema": "royalebench.dataset-manifest.v1",
        "dataset_version": 1,
        "created_by": "royalebench",
        "split_seed": int(split_seed),
        "split_policy": "stable-sha256-seed-cluster-level",
        "engine": first_engine,
        "matches_root": str(source_root),
        "total_matches": len(sources),
        "splits": {
            split: {
                "path": path.name,
                "matches": transition_matches[split],
                "seed_groups": sorted({source.seed for source in split_sources[split]}),
                "match_count": len(transition_matches[split]),
                "transition_count": transition_counts[split],
                "sha256": _file_sha256(path),
            }
            for split, path in paths.items()
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
