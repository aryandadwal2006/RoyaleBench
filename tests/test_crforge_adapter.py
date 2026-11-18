from __future__ import annotations

from types import SimpleNamespace

import pytest

from royalebench.config import V1Config
from royalebench.engine.crforge import (
    CrforgeEngineError,
    _validate_initial_observations,
    _validate_runtime_metadata,
)


def _metadata(**overrides):
    config = {
        "decision_ticks": 5,
        "level": 11,
        "tower_level": 11,
        "max_ticks": 9000,
    }
    config.update(overrides.pop("config", {}))
    return {"config": config, "mask_version": overrides.pop("mask_version", 1)}


def _observations():
    deck = [
        "Cannon",
        "Fireball",
        "HogRider",
        "IceGolem",
        "IceSpirit",
        "Musketeer",
        "Skeletons",
        "Log",
    ]
    seats = []
    for seat in (0, 1):
        seats.append(
            {
                "seat": seat,
                "game": {"tick": 0, "decision_ticks": 5, "play_delay_ticks": 20},
                "own": {
                    "deck": list(deck),
                    "deck_level": [11] * 8,
                    "elixir_scaled": 50000,
                    "towers": {
                        "own_king": {"max_hp": 5000},
                        "own_left": {"max_hp": 3000},
                        "own_right": {"max_hp": 3000},
                    },
                },
                "opponent": {
                    "estimated_elixir_scaled": 50000,
                    "towers": {
                        "enemy_king": {"max_hp": 5000},
                        "enemy_left": {"max_hp": 3000},
                        "enemy_right": {"max_hp": 3000},
                    },
                },
            }
        )
    return tuple(seats)


def test_runtime_metadata_accepts_the_frozen_crforge_contract():
    _validate_runtime_metadata(
        _metadata(),
        config=V1Config(),
        decision_ticks=5,
        schema=SimpleNamespace(play_delay_ticks=20),
        id_version=2,
    )


@pytest.mark.parametrize(
    ("metadata", "decision_ticks", "delay", "id_version", "message"),
    [
        (_metadata(config={"level": 10}), 5, 20, 2, "config mismatch for level"),
        (_metadata(config={"tower_level": 10}), 5, 20, 2, "config mismatch for tower_level"),
        (_metadata(config={"decision_ticks": 20}), 5, 20, 2, "config mismatch for decision_ticks"),
        (_metadata(config={"max_ticks": 8000}), 5, 20, 2, "config mismatch for max_ticks"),
        (_metadata(mask_version=2), 5, 20, 2, "mask_version"),
        (_metadata(), 5, 19, 2, "delay is 19"),
        (_metadata(), 5, 20, 1, "id_version is 1"),
    ],
)
def test_runtime_metadata_rejects_semantic_drift(
    metadata, decision_ticks, delay, id_version, message
):
    with pytest.raises(CrforgeEngineError, match=message):
        _validate_runtime_metadata(
            metadata,
            config=V1Config(),
            decision_ticks=decision_ticks,
            schema=SimpleNamespace(play_delay_ticks=delay),
            id_version=id_version,
        )


def test_runtime_metadata_requires_effective_config():
    with pytest.raises(CrforgeEngineError, match="does not expose"):
        _validate_runtime_metadata(
            {"mask_version": 1},
            config=V1Config(),
            decision_ticks=5,
            schema=SimpleNamespace(play_delay_ticks=20),
            id_version=2,
        )


def test_initial_observations_accept_equal_mirrored_match():
    _validate_initial_observations(
        _observations(),
        deck_rows=tuple(_observations()[0]["own"]["deck"]),
        config=V1Config(),
        decision_ticks=5,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda obs: obs[0].update(seat=1), "observation slot 0"),
        (lambda obs: obs[1]["own"].update(deck_level=[10] * 8), "deck levels"),
        (lambda obs: obs[0]["own"].update(deck=obs[0]["own"]["deck"][:-1]), "different from"),
        (lambda obs: obs[0]["game"].update(decision_ticks=20), "decision_ticks"),
        (lambda obs: obs[1]["game"].update(play_delay_ticks=10), "play_delay_ticks"),
        (
            lambda obs: obs[0]["opponent"]["towers"]["enemy_right"].update(max_hp=2500),
            "princess tower max HP",
        ),
        (
            lambda obs: obs[1]["opponent"].update(estimated_elixir_scaled=40000),
            "initial public opponent elixir",
        ),
    ],
)
def test_initial_observations_reject_mismatched_v1_setup(mutation, message):
    observations = [dict(item) for item in _observations()]
    for item in observations:
        item["own"] = dict(item["own"])
        item["game"] = dict(item["game"])
        item["opponent"] = dict(item["opponent"])
        item["own"]["towers"] = dict(item["own"]["towers"])
        item["opponent"]["towers"] = dict(item["opponent"]["towers"])
        for tower in item["own"]["towers"].values():
            tower.copy()
        for tower in item["opponent"]["towers"].values():
            tower.copy()
    # Make nested tower dictionaries independent before applying a one-field mutation.
    for item in observations:
        item["own"]["towers"] = {key: dict(value) for key, value in item["own"]["towers"].items()}
        item["opponent"]["towers"] = {
            key: dict(value) for key, value in item["opponent"]["towers"].items()
        }
    mutation(observations)
    with pytest.raises(CrforgeEngineError, match=message):
        _validate_initial_observations(
            tuple(observations),
            deck_rows=tuple(_observations()[0]["own"]["deck"]),
            config=V1Config(),
            decision_ticks=5,
        )
