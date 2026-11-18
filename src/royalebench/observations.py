"""Convert CRForge's seat-visible integer observation into RoyaleBench ObservationV1."""

import hashlib
import json
from typing import Any

import numpy as np

from royalebench.public_memory import derive_opponent_cycle

OBSERVATION_SCHEMA = "royalebench.observation.v1"


def _ints(value: Any) -> list[int]:
    return [int(item) for item in np.asarray(value).reshape(-1).tolist()]


def _int(value: Any) -> int:
    values = np.asarray(value).reshape(-1)
    if values.size != 1:
        raise ValueError(f"expected a scalar observation field, got {values.size} values")
    return int(values[0])


def _name(vocabulary: list[str], value: int) -> str | None:
    return vocabulary[value] if 0 <= value < len(vocabulary) else None


def _named(values: list[int], vocabulary: list[str]) -> list[str]:
    return [name for value in values if (name := _name(vocabulary, value)) is not None]


def _entity_payload(schema: Any, vocabulary: list[str], row: np.ndarray) -> dict[str, Any]:
    entity = {name: int(row[index]) for name, index in schema.entity.items()}
    entity["row_name"] = _name(vocabulary, entity["row"])
    kind_by_code = {code: name for name, code in schema.kinds.items()}
    entity["kind_name"] = kind_by_code.get(entity["kind"], "unknown")
    entity["state_name"] = (
        schema.state_names[entity["state"]]
        if 0 <= entity["state"] < len(schema.state_names)
        else None
    )
    entity["flag_names"] = [
        name for name, bit in schema.flags.items() if entity["flags"] & bit
    ]
    entity["x_tiles"] = entity["x"] / schema.tile_units
    entity["y_tiles"] = entity["y"] / schema.tile_units
    return entity


def build_observation(
    vector: Any,
    raw_observation: np.ndarray,
    action_mask: np.ndarray,
    *,
    match_id: str,
    decision_id: int,
    seat: int,
) -> dict[str, Any]:
    """Build a public-only observation from the CRForge seat view.

    CRForge applies its seat visibility rules before writing these rows. This converter preserves
    unknown values (-1) and does not read the underlying battle objects or enemy state.
    """
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    schema = vector.schema
    vocabulary = vector.vocabulary

    def scalar(name: str) -> int:
        return _int(schema.field(raw_observation, name))

    def values(name: str) -> list[int]:
        return _ints(schema.field(raw_observation, name))

    hand_ids = values("hand_card")
    hand_costs = values("hand_cost")
    hand_pending = values("hand_pending")
    hand_forms = values("hand_form")
    elixir_scale = int(schema.scales.get("elixir_scale", 10_000))
    if elixir_scale <= 0:
        raise RuntimeError(f"invalid CRForge elixir scale: {elixir_scale}")
    hand = [
        {
            "slot": slot,
            "card": _name(vocabulary, card_id),
            "cost_elixir_scaled": hand_costs[slot],
            "cost_elixir": hand_costs[slot] / elixir_scale,
            "pending": bool(hand_pending[slot]),
            "form": hand_forms[slot],
        }
        for slot, card_id in enumerate(hand_ids)
    ]

    deck = _named(values("deck"), vocabulary)
    next_card = _name(vocabulary, scalar("next_card"))
    enemy_seen = _named(values("enemy_seen"), vocabulary)

    tower_names = (
        "own_king",
        "own_left",
        "own_right",
        "enemy_king",
        "enemy_left",
        "enemy_right",
    )
    towers = {
        name: {
            "hp": scalar(f"{name}_hp"),
            "max_hp": scalar(f"{name}_max_hp"),
        }
        for name in tower_names
    }

    pending_count = scalar("pending_count")
    pending_cards = values("pending_card")
    pending_x = values("pending_x")
    pending_y = values("pending_y")
    pending_ticks = values("pending_ticks")
    pending = [
        {
            "card": _name(vocabulary, pending_cards[index]),
            "x_units": pending_x[index],
            "y_units": pending_y[index],
            "ticks_until_run": pending_ticks[index],
        }
        for index in range(min(pending_count, len(pending_cards)))
    ]

    ability_fields = {
        name: values(f"ability_{name}")
        for name in ("champion", "unit", "state", "cooldown_ms", "charges", "command_ticks")
    }
    abilities = []
    for slot in range(schema.ability_slots):
        champion = ability_fields["champion"][slot]
        abilities.append(
            {
                "slot": slot,
                "champion": _name(vocabulary, champion),
                "unit_id": ability_fields["unit"][slot],
                "state": ability_fields["state"][slot],
                "cooldown_ms": ability_fields["cooldown_ms"][slot],
                "charges": ability_fields["charges"][slot],
                "command_ticks": ability_fields["command_ticks"][slot],
            }
        )

    play_fields = {
        name: values(f"enemy_play_{name}")
        for name in ("card", "cast", "form", "ticks", "x", "y", "kind", "flags", "point_ticks")
    }
    card_shown_bit = schema.play_flags.get("card_shown")
    point_shown_bit = schema.play_flags.get("point_shown")
    if card_shown_bit is None:
        raise RuntimeError("CRForge schema does not expose the enemy-play card_shown flag")
    recent_plays = []
    for index in range(schema.enemy_play_rows):
        recent_plays.append(
            {
                "card": _name(vocabulary, play_fields["card"][index]),
                "cast_as": _name(vocabulary, play_fields["cast"][index]),
                "form": play_fields["form"][index],
                "ticks_since_play": play_fields["ticks"][index],
                "x_units": play_fields["x"][index],
                "y_units": play_fields["y"][index],
                "kind": play_fields["kind"][index],
                "flags": play_fields["flags"][index],
                "card_shown": bool(play_fields["flags"][index] & card_shown_bit),
                "point_shown": (
                    bool(play_fields["flags"][index] & point_shown_bit)
                    if point_shown_bit is not None
                    else False
                ),
                "ticks_since_point_shown": play_fields["point_ticks"][index],
            }
        )

    opponent_cycle = derive_opponent_cycle(
        deck,
        recent_plays,
        play_count=scalar("enemy_play_count"),
    )

    rows = schema.entities(raw_observation)
    entities = [_entity_payload(schema, vocabulary, row) for row in rows]

    playable_slots: list[int] = []
    tiles_per_slot = schema.cols * schema.rows
    for slot in range(schema.hand_slots):
        start = 1 + slot * tiles_per_slot
        legal = np.asarray(action_mask[start : start + tiles_per_slot], dtype=np.uint8)
        opened = int(np.count_nonzero(legal))
        if vector.mask_version == 1 and opened not in (0, tiles_per_slot):
            raise RuntimeError(
                f"CRForge MASK_ALL_TILES invariant failed for hand slot {slot}: "
                f"{opened}/{tiles_per_slot} tiles open"
            )
        if opened:
            playable_slots.append(slot)

    ability_slots = [
        slot
        for slot in range(schema.ability_slots)
        if bool(action_mask[schema.first_ability + slot])
    ]

    payload = {
        "schema": OBSERVATION_SCHEMA,
        "match_id": match_id,
        "decision_id": decision_id,
        "seat": seat,
        "game": {
            "tick": scalar("tick"),
            "time_ms": scalar("time_ms"),
            "section": scalar("section"),
            "section_type": scalar("section_type"),
            "section_left_ms": scalar("section_left_ms"),
            "overtime": bool(scalar("overtime")),
            "decision_ticks": scalar("decision_ticks"),
            "play_delay_ticks": scalar("play_delay_ticks"),
            "result": scalar("result"),
        },
        "own": {
            "elixir_scaled": scalar("elixir"),
            "elixir": scalar("elixir") / elixir_scale,
            "elixir_reserved_scaled": scalar("elixir_reserved"),
            "elixir_reserved": scalar("elixir_reserved") / elixir_scale,
            "hand": hand,
            "next_card": next_card,
            "deck": deck,
            "queue": _named(values("queue"), vocabulary),
            "towers": {name: towers[name] for name in tower_names[:3]},
            "pending": pending,
            "abilities": abilities,
            "illegal_actions_total": scalar("illegal"),
        },
        "opponent": {
            "estimated_elixir_scaled": scalar("enemy_elixir"),
            "estimated_elixir": scalar("enemy_elixir") / elixir_scale,
            "elixir_estimate_source": "crforge-public-play-and-regeneration-accounting",
            "cards_seen": enemy_seen,
            "play_count": scalar("enemy_play_count"),
            "recent_plays": recent_plays,
            "card_cycle": opponent_cycle,
            "towers": {name: towers[name] for name in tower_names[3:]},
        },
        "entities": entities,
        "legal_actions": {
            "playable_slots": playable_slots,
            "ability_slots": ability_slots,
            "tile_grid": {
                "cols": schema.cols,
                "rows": schema.rows,
                "resolution": "tile-center-v1",
            },
            "mask_rule": "all-tap-tiles-v1",
        },
        "engine": {
            "schema_version": schema.version,
            "data_version": vector.data_version,
            "content_sha": vector.content_sha,
            "vocabulary_hash": vector.vocabulary_hash,
            "elixir_scale": elixir_scale,
            "tile_units": schema.tile_units,
        },
    }
    return payload


def observation_hash(observation: dict[str, Any]) -> str:
    """Stable SHA-256 of an ObservationV1 payload."""
    canonical = json.dumps(
        observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
