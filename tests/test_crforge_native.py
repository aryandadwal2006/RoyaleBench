from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from royalebench.config import V1Config
from royalebench.engine.crforge import _resolve_deck_rows


def _engine_paths(config: V1Config) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    install = Path(
        os.environ.get(
            "ROYALEBENCH_CRFORGE_INSTALL",
            root / "third_party" / "upstream" / "crforge" / "env" / "build" / "install" / "env",
        )
    )
    tables = Path(
        os.environ.get(
            "ROYALEBENCH_CRFORGE_TABLES",
            Path.home() / ".crforge" / "tables" / config.data_version,
        )
    )
    return install, tables


def _vector(config: V1Config, decision_ticks: int = 5):
    install, tables = _engine_paths(config)
    if not install.is_dir() or not tables.is_dir():
        pytest.skip("pinned CRForge install or game tables are not available")
    try:
        from crforge_env import LadderConfig, VectorBattle
    except ImportError:
        pytest.skip("crforge-env is not installed in this Python environment")

    ladder_config = LadderConfig(
        decision_ticks=decision_ticks,
        level=config.card_level,
        tower_level=config.tower_level,
        max_ticks=config.max_ticks,
        mask_version=config.mask_version,
    )
    vector = VectorBattle(
        1,
        1,
        install=install,
        engine="ladder",
        tables=tables,
        config=ladder_config,
    )
    vector.set_autoreset(False)
    if vector.data_version != config.data_version:
        vector.close()
        pytest.fail(
            f"wrong game-data version: expected {config.data_version}, got {vector.data_version}"
        )
    return vector


def _king_row(vector, seat: int, relative_side: int):
    schema = vector.schema
    rows = schema.entities(vector.observations[0, seat])
    matches = [
        row
        for row in rows
        if int(row[schema.entity["kind"]]) == schema.kinds["tower"]
        and int(row[schema.entity["side"]]) == relative_side
        and int(row[schema.entity["flags"]]) & schema.flags["king"]
    ]
    assert len(matches) == 1
    return matches[0]


def test_seat_frames_are_half_turn_transforms_on_native_tower_entities():
    config = V1Config()
    with _vector(config) as vector:
        deck = _resolve_deck_rows(config.deck, vector.vocabulary)
        vector.reset([20261118], deck, deck)

        # Physical side 0 is own to seat 0 and enemy to seat 1.
        side0_as_own = _king_row(vector, seat=0, relative_side=0)
        side0_as_enemy = _king_row(vector, seat=1, relative_side=1)
        x = vector.schema.entity["x"]
        y = vector.schema.entity["y"]
        assert int(side0_as_own[x]) + int(side0_as_enemy[x]) == vector.schema.width_units
        assert int(side0_as_own[y]) + int(side0_as_enemy[y]) == vector.schema.height_units

        # Physical side 1 is enemy to seat 0 and own to seat 1.
        side1_as_enemy = _king_row(vector, seat=0, relative_side=1)
        side1_as_own = _king_row(vector, seat=1, relative_side=0)
        assert int(side1_as_enemy[x]) + int(side1_as_own[x]) == vector.schema.width_units
        assert int(side1_as_enemy[y]) + int(side1_as_own[y]) == vector.schema.height_units


def test_unseen_opponent_deck_does_not_change_the_other_seats_initial_view():
    config = V1Config()
    basic = ("Knight", "Archer", "Musketeer", "Giant", "MiniPekka", "Fireball", "Arrows", "Zap")
    with _vector(config) as first, _vector(config) as second:
        deck = _resolve_deck_rows(config.deck, first.vocabulary)
        alternative = _resolve_deck_rows(basic, first.vocabulary)
        first.reset([731], deck, alternative)
        second.reset([731], deck, tuple(reversed(alternative)))

        np.testing.assert_array_equal(first.observations[0, 0], second.observations[0, 0])
        np.testing.assert_array_equal(first.masks[0, 0], second.masks[0, 0])
        assert not np.array_equal(first.observations[0, 1], second.observations[0, 1])


def test_hog_v1_public_enemy_elixir_matches_native_truth_during_play():
    config = V1Config()
    rng = np.random.default_rng(20261118)
    with _vector(config) as vector:
        deck = _resolve_deck_rows(config.deck, vector.vocabulary)
        vector.reset([919], deck, deck)
        field = vector.schema.header["enemy_elixir"][0]

        for decision in range(160):
            actions = np.zeros((1, 2), dtype=np.int32)
            for seat in (0, 1):
                legal = np.flatnonzero(vector.masks[0, seat])
                if len(legal) > 1 and rng.random() < 0.35:
                    actions[0, seat] = int(rng.choice(legal[legal != vector.schema.wait]))
            vector.step(actions)

            native_env = vector._env.env(0)
            battle = native_env.battle()
            for seat in (0, 1):
                counted = int(vector.observations[0, seat, field])
                truth = int(battle.getMatch().side(1 - seat).getElixir())
                assert counted == truth, (
                    f"decision {decision}, seat {seat}: public enemy elixir {counted} "
                    f"differs from native side elixir {truth}"
                )
            if bool(vector.dones[0]):
                break
