from __future__ import annotations

import gzip
import json

from royalebench.dataset import build_dataset


def write_match(root, match_id, seed):
    match_dir = root / match_id
    match_dir.mkdir(parents=True)
    manifest = {
        "match_id": match_id,
        "seed": seed,
        "engine": {"data_version": "16.635.8", "content_sha": "abc"},
    }
    result = {
        "match_id": match_id,
        "status": "completed",
        "outcome": "draw",
    }
    (match_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (match_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    transition = {
        "seat": 0,
        "engine_tick": 5,
        "observation": {"decision_id": 0},
        "next_observation": {"decision_id": 1},
        "response": {
            "action": {"schema": "royalebench.action.v1", "type": "wait"}
        },
        "observation_hash": "a" * 64,
        "next_observation_hash": "b" * 64,
    }
    with gzip.open(match_dir / "trajectory.jsonl.gz", "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(transition) + "\n")


def test_dataset_splits_complete_matches_without_leakage(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    for index in range(5):
        write_match(matches, f"match-{index}", index)

    output = tmp_path / "dataset"
    first = build_dataset(matches, output, split_seed=12)
    second = build_dataset(matches, output, split_seed=12)

    groups = [set(row["matches"]) for row in first["splits"].values()]
    assert not (groups[0] & groups[1])
    assert not (groups[0] & groups[2])
    assert not (groups[1] & groups[2])
    assert sum(row["match_count"] for row in first["splits"].values()) == 5
    assert all(row["transition_count"] == row["match_count"] for row in first["splits"].values())
    assert first["splits"] == second["splits"]
    assert (output / "dataset_manifest.json").exists()


def test_dataset_requires_three_completed_matches(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    for index in range(2):
        write_match(matches, f"match-{index}", index)
    try:
        build_dataset(matches, tmp_path / "dataset")
    except ValueError as exc:
        assert "at least three" in str(exc)
    else:
        raise AssertionError("expected too-few-matches error")
