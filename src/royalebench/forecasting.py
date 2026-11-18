"""Action-conditioned world-model forecast evaluation on held-out JSONL shards.

Predictors receive only the source observation and the intervening actions. Dataset
labels, match outcomes and future observations are never passed to the predictor.
"""

from __future__ import annotations

import copy
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Protocol


class Forecaster(Protocol):
    name: str

    def predict(
        self,
        observation: dict[str, Any],
        actions: list[dict[str, Any]],
        *,
        horizon_ticks: int,
    ) -> dict[str, Any]: ...


class PersistenceForecaster:
    """No-change baseline: predict that the current visible state persists."""

    name = "persistence-v1"

    def predict(
        self,
        observation: dict[str, Any],
        actions: list[dict[str, Any]],
        *,
        horizon_ticks: int,
    ) -> dict[str, Any]:
        del actions, horizon_ticks
        return copy.deepcopy(observation)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _numeric_errors(
    predicted: dict[str, Any],
    actual: dict[str, Any],
    paths: list[tuple[str, ...]],
) -> list[float]:
    errors = []
    for path in paths:
        left: Any = predicted
        right: Any = actual
        try:
            for key in path:
                left = left[key]
                right = right[key]
        except (KeyError, TypeError):
            continue
        p_value = _number(left)
        a_value = _number(right)
        if p_value is not None and a_value is not None:
            errors.append(abs(p_value - a_value))
    return errors


def _entity_type_counts(observation: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    entities = observation.get("entities")
    if not isinstance(entities, list):
        return counts
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        label = entity.get("row_name") or entity.get("kind_name")
        if isinstance(label, str) and label:
            counts[label] += 1
    return counts


def _score_pair(
    predicted: dict[str, Any], actual: dict[str, Any]
) -> dict[str, float]:
    tower_paths = [
        (side, "towers", tower, "hp")
        for side in ("own", "opponent")
        for tower in ("own_king", "own_left", "own_right", "enemy_king", "enemy_left", "enemy_right")
    ]
    elixir_paths = [
        ("own", "elixir"),
        ("opponent", "estimated_elixir"),
    ]
    tower_errors = _numeric_errors(predicted, actual, tower_paths)
    elixir_errors = _numeric_errors(predicted, actual, elixir_paths)
    predicted_entities = _entity_type_counts(predicted)
    actual_entities = _entity_type_counts(actual)
    true_positive = sum(
        min(count, actual_entities.get(label, 0))
        for label, count in predicted_entities.items()
    )
    predicted_count = sum(predicted_entities.values())
    actual_count = sum(actual_entities.values())
    precision = true_positive / predicted_count if predicted_count else float(actual_count == 0)
    recall = true_positive / actual_count if actual_count else float(predicted_count == 0)
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "tower_hp_mae": sum(tower_errors) / len(tower_errors) if tower_errors else 0.0,
        "tower_hp_values": float(len(tower_errors)),
        "elixir_mae": sum(elixir_errors) / len(elixir_errors) if elixir_errors else 0.0,
        "elixir_values": float(len(elixir_errors)),
        "entity_type_precision": precision,
        "entity_type_recall": recall,
        "entity_type_f1": f1,
        "predicted_entity_count": float(predicted_count),
        "actual_entity_count": float(actual_count),
        "entity_count_absolute_error": float(abs(predicted_count - actual_count)),
    }


def evaluate_forecaster(
    split_path: str | Path,
    forecaster: Forecaster,
    *,
    horizons: tuple[int, ...] = (1, 2, 4),
) -> dict[str, Any]:
    """Evaluate forecasts at N decision intervals using only prior observations/actions."""
    if not horizons or any(not isinstance(h, int) or h < 1 for h in horizons):
        raise ValueError("horizons must contain positive integer decision intervals")
    if len(set(horizons)) != len(horizons):
        raise ValueError("horizons must be unique")

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    with gzip.open(split_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("schema") != "royalebench.transition.v1":
                raise ValueError(f"unsupported transition schema at line {line_number}")
            grouped[(str(record["match_id"]), int(record["seat"]))].append(record)

    totals: dict[int, dict[str, float]] = {
        horizon: defaultdict(float) for horizon in horizons
    }
    counts = {horizon: 0 for horizon in horizons}
    for records in grouped.values():
        records.sort(key=lambda item: int(item["decision_id"]))
        for horizon in horizons:
            for start in range(0, len(records) - horizon + 1):
                source = records[start]
                target = records[start + horizon - 1]
                observation = source["observation"]
                actual = target["next_observation"]
                actions = [row["action"] for row in records[start : start + horizon]]
                start_tick = int(source["engine_tick"])
                end_tick = int(target["next_observation"]["game"]["tick"])
                horizon_ticks = end_tick - start_tick
                if horizon_ticks < 1:
                    raise ValueError("forecast target tick must follow source engine tick")
                prediction = forecaster.predict(
                    copy.deepcopy(observation),
                    copy.deepcopy(actions),
                    horizon_ticks=horizon_ticks,
                )
                if not isinstance(prediction, dict):
                    raise TypeError("forecaster.predict must return an ObservationV1 object")
                metrics = _score_pair(prediction, actual)
                for key, value in metrics.items():
                    totals[horizon][key] += value
                counts[horizon] += 1

    results = {}
    for horizon in horizons:
        count = counts[horizon]
        if count == 0:
            raise ValueError(
                f"no examples available for horizon {horizon}; provide longer match trajectories"
            )
        values = {}
        for key, total in totals[horizon].items():
            values[key] = total / count
        values["examples"] = count
        results[str(horizon)] = values

    return {
        "schema": "royalebench.forecast-evaluation.v1",
        "forecaster": forecaster.name,
        "split_path": str(Path(split_path)),
        "horizon_unit": "decision_intervals",
        "horizons": results,
        "input_contract": "source_observation_plus_intervening_actions_only",
        "labels_excluded_from_predictor_input": [
            "match_outcome",
            "next_observation",
            "future_observations",
        ],
    }


def write_forecast_report(report: dict[str, Any], output_path: str | Path) -> None:
    destination = Path(output_path)
    if destination.exists():
        raise FileExistsError(f"forecast report already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
