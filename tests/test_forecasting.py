from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from royalebench.forecasting import PersistenceForecaster, evaluate_forecaster, write_forecast_report
from royalebench.observations import observation_hash


def _observation(tick: int, *, hp: int = 100, elixir: float = 5.0) -> dict:
    towers = {
        "own_king": {"hp": hp},
        "own_left": {"hp": hp},
        "own_right": {"hp": hp},
    }
    enemy_towers = {
        "enemy_king": {"hp": hp},
        "enemy_left": {"hp": hp},
        "enemy_right": {"hp": hp},
    }
    return {
        "schema": "royalebench.observation.v1",
        "match_id": "forecast-match",
        "decision_id": tick,
        "seat": 0,
        "game": {"tick": tick},
        "own": {"elixir": elixir, "towers": towers},
        "opponent": {"estimated_elixir": elixir, "towers": enemy_towers},
        "entities": [],
        "legal_actions": {},
        "engine": {},
    }


def _write_split(path, length=5):
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for index in range(length):
            observation = _observation(index * 5)
            next_observation = _observation((index + 1) * 5)
            record = {
                "schema": "royalebench.transition.v1",
                "match_id": "forecast-match",
                "seed": 9,
                "seat": 0,
                "decision_id": index,
                "engine_tick": index * 5,
                "action": {"schema": "royalebench.action.v1", "type": "wait"},
                "observation": observation,
                "next_observation": next_observation,
                "observation_hash": observation_hash(observation),
                "next_observation_hash": observation_hash(next_observation),
                "match_outcome": "seat0_win",
            }
            handle.write(json.dumps(record) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "dataset_version": 1,
        "splits": {"test": {"path": path.name, "sha256": digest}},
    }
    (path.parent / "dataset_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_persistence_forecaster_scores_perfectly_on_static_trajectory(tmp_path):
    split = tmp_path / "test.jsonl.gz"
    _write_split(split)
    report = evaluate_forecaster(split, PersistenceForecaster(), horizons=(1, 2, 3))
    assert report["forecaster"] == "persistence-v1"
    assert report["horizon_unit"] == "decision_intervals"
    for metrics in report["horizons"].values():
        assert metrics["tower_hp_mae"] == 0
        assert metrics["elixir_mae"] == 0
        assert metrics["entity_type_f1"] == 1
    assert report["labels_excluded_from_predictor_input"] == [
        "match_outcome",
        "next_observation",
        "future_observations",
    ]


def test_forecaster_receives_only_current_observation_and_action_prefix(tmp_path):
    split = tmp_path / "test.jsonl.gz"
    _write_split(split, length=4)

    class RecordingForecaster:
        name = "recording-test"

        def __init__(self):
            self.calls = []

        def predict(self, observation, actions, *, horizon_ticks):
            self.calls.append((observation, actions, horizon_ticks))
            return observation

    model = RecordingForecaster()
    report = evaluate_forecaster(split, model, horizons=(1, 2))
    assert report["horizons"]["1"]["examples"] == 4
    assert report["horizons"]["2"]["examples"] == 3
    assert len(model.calls) == 7
    assert all("match_outcome" not in observation for observation, _, _ in model.calls)
    assert [len(actions) for _, actions, _ in model.calls] == [1] * 4 + [2] * 3
    assert all(ticks > 0 for _, _, ticks in model.calls)


def test_forecast_evaluator_rejects_unavailable_horizon(tmp_path):
    split = tmp_path / "test.jsonl.gz"
    _write_split(split, length=2)
    with pytest.raises(ValueError, match="no examples available"):
        evaluate_forecaster(split, PersistenceForecaster(), horizons=(3,))


def test_forecast_report_refuses_to_overwrite(tmp_path):
    destination = tmp_path / "report.json"
    destination.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_forecast_report({"schema": "test"}, destination)

def test_forecast_evaluator_rejects_corrupted_observation_hash(tmp_path):
    split = tmp_path / "test.jsonl.gz"
    _write_split(split)
    with gzip.open(split, "rt", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    records[0]["observation_hash"] = "0" * 64
    with gzip.open(split, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    manifest = json.loads((tmp_path / "dataset_manifest.json").read_text())
    manifest["splits"]["test"]["sha256"] = hashlib.sha256(split.read_bytes()).hexdigest()
    (tmp_path / "dataset_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="observation hash mismatch"):
        evaluate_forecaster(split, PersistenceForecaster(), horizons=(1,))


def test_forecast_evaluator_rejects_modified_dataset_shard(tmp_path):
    split = tmp_path / "test.jsonl.gz"
    _write_split(split)
    split.write_bytes(split.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        evaluate_forecaster(split, PersistenceForecaster(), horizons=(1,))
