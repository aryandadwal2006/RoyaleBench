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
    repeat_output = tmp_path / "dataset-repeat"
    first = build_dataset(matches, output, split_seed=12)
    second = build_dataset(matches, repeat_output, split_seed=12)

    groups = [set(row["seed_groups"]) for row in first["splits"].values()]
    assert not (groups[0] & groups[1])
    assert not (groups[0] & groups[2])
    assert not (groups[1] & groups[2])
    assert sum(row["match_count"] for row in first["splits"].values()) == 5
    assert all(row["transition_count"] == row["match_count"] for row in first["splits"].values())
    assert first["splits"] == second["splits"]
    assert (output / "dataset_manifest.json").exists()
    for split in ("train", "validation", "test"):
        first_bytes = (output / f"{split}.jsonl.gz").read_bytes()
        second_bytes = (repeat_output / f"{split}.jsonl.gz").read_bytes()
        assert first_bytes == second_bytes


def test_paired_side_swapped_matches_share_the_same_split(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    for seed in range(3):
        write_match(matches, f"pair-a-seed-{seed}-seat0", seed)
        write_match(matches, f"pair-a-seed-{seed}-seat1", seed)

    manifest = build_dataset(matches, tmp_path / "dataset")
    groups = [set(row["seed_groups"]) for row in manifest["splits"].values()]
    assert sorted(len(group) for group in groups) == [1, 1, 1]
    for split in manifest["splits"].values():
        for seed in split["seed_groups"]:
            same_seed_matches = {
                f"pair-a-seed-{seed}-seat0",
                f"pair-a-seed-{seed}-seat1",
            }
            assert same_seed_matches.issubset(set(split["matches"]))


def test_dataset_requires_three_distinct_seed_groups(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    write_match(matches, "pair-seat0", 1)
    write_match(matches, "pair-seat1", 1)
    try:
        build_dataset(matches, tmp_path / "dataset")
    except ValueError as exc:
        assert "three distinct simulator seed groups" in str(exc)
    else:
        raise AssertionError("expected too-few-seed-groups error")



def test_dataset_refuses_to_overwrite_existing_artifacts(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    for index in range(3):
        write_match(matches, f"match-{index}", index)

    output = tmp_path / "dataset"
    build_dataset(matches, output)
    original = (output / "train.jsonl.gz").read_bytes()

    try:
        build_dataset(matches, output)
    except FileExistsError as exc:
        assert "choose a new output directory" in str(exc)
    else:
        raise AssertionError("expected existing-dataset protection")

    assert (output / "train.jsonl.gz").read_bytes() == original
