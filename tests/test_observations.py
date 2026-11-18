from __future__ import annotations

import numpy as np

from royalebench.observations import build_observation, observation_hash


class FakeSchema:
    version = 4
    cols = 18
    rows = 32
    tile_units = 2
    hand_slots = 4
    ability_slots = 2
    first_ability = 1 + hand_slots * cols * rows
    enemy_play_rows = 8
    entity = {}
    kinds = {"character": 1}
    flags = {"alive": 1}
    play_flags = {"card_shown": 1, "point_shown": 2}
    state_names = []
    scales = {"elixir_scale": 10_000}

    @staticmethod
    def field(raw, name):
        return raw[name]

    @staticmethod
    def entities(raw):
        del raw
        return np.empty((0, 0), dtype=np.int32)


class FakeVector:
    schema = FakeSchema()
    vocabulary = [
        "Cannon", "Fireball", "HogRider", "IceGolem",
        "IceSpirit", "Musketeer", "Skeletons", "Log",
    ]
    mask_version = 1
    data_version = "16.635.8"
    content_sha = "test-content-sha"
    vocabulary_hash = "test-vocabulary-hash"


def raw_seat_view():
    raw = {
        "hand_card": np.array([0, 1, 2, 3]),
        "hand_cost": np.array([3, 4, 1, 2]),
        "hand_pending": np.zeros(4, dtype=np.int32),
        "hand_form": np.zeros(4, dtype=np.int32),
        "deck": np.arange(8),
        "next_card": np.array([4]),
        "enemy_seen": np.array([], dtype=np.int32),
        "pending_count": np.array([0]),
        "pending_card": np.full(4, -1),
        "pending_x": np.zeros(4),
        "pending_y": np.zeros(4),
        "pending_ticks": np.zeros(4),
        "queue": np.array([4, 5, 6, 7]),
        "enemy_play_count": np.array([0]),
        "elixir": np.array([50_000]),
        "elixir_reserved": np.array([10_000]),
        "enemy_elixir": np.array([42_000]),
        "illegal": np.array([0]),
        "tick": np.array([100]),
        "time_ms": np.array([5000]),
        "section": np.array([0]),
        "section_type": np.array([0]),
        "section_left_ms": np.array([100_000]),
        "overtime": np.array([0]),
        "decision_ticks": np.array([5]),
        "play_delay_ticks": np.array([20]),
        "result": np.array([0]),
    }
    for name in ("own_king", "own_left", "own_right", "enemy_king", "enemy_left", "enemy_right"):
        raw[f"{name}_hp"] = np.array([1000])
        raw[f"{name}_max_hp"] = np.array([2000])
    for name in ("champion", "unit", "state", "cooldown_ms", "charges", "command_ticks"):
        raw[f"ability_{name}"] = np.zeros(2, dtype=np.int32)
    for name in ("card", "cast", "form", "ticks", "x", "y", "kind", "flags", "point_ticks"):
        raw[f"enemy_play_{name}"] = np.full(8, -1 if name in {"card", "cast"} else 0)
    return raw


def test_observation_exposes_normalized_elixir_but_not_hidden_state():
    vector = FakeVector()
    mask = np.zeros(vector.schema.first_ability + 2, dtype=np.uint8)
    mask[1 : 1 + vector.schema.cols * vector.schema.rows] = 1
    raw = raw_seat_view()

    observation = build_observation(
        vector, raw, mask, match_id="fake-match", decision_id=7, seat=0
    )

    assert observation["own"]["elixir"] == 5.0
    assert observation["own"]["elixir_reserved"] == 1.0
    assert observation["own"]["hand"][0]["cost_elixir"] == 3.0
    assert observation["opponent"]["estimated_elixir"] == 4.2
    assert observation["opponent"]["card_cycle"]["hand_exact"] is False
    assert observation["legal_actions"]["playable_slots"] == [0]
    assert "enemy_hand" not in observation["opponent"]
    assert "true_enemy_elixir" not in observation["opponent"]
    assert "internal_state" not in observation
    assert len(observation_hash(observation)) == 64


def test_observation_keeps_crforge_raw_scaled_values_for_audit():
    vector = FakeVector()
    mask = np.zeros(vector.schema.first_ability + 2, dtype=np.uint8)
    observation = build_observation(
        vector, raw_seat_view(), mask, match_id="fake-match", decision_id=0, seat=1
    )
    assert observation["own"]["elixir_scaled"] == 50_000
    assert observation["opponent"]["estimated_elixir_scaled"] == 42_000
    assert observation["seat"] == 1
