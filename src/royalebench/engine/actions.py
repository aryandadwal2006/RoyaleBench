"""Translate RoyaleBench actions into CRForge's integer action codec."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from royalebench.protocol.actions import (
    AbilityAction,
    ActionResolution,
    PlayAction,
    WaitAction,
    action_from_mapping,
)


def to_crforge_action(
    raw_action: object,
    *,
    schema: Any,
    raw_observation: np.ndarray,
    action_mask: np.ndarray,
    card_name_lookup: Callable[[int], str | None],
) -> tuple[int, bool]:
    """Return (CRForge action integer, mask-open flag).

    Coordinates are never snapped. An invalid/stale card-slot binding is rejected before
    execution. A strategically poor but structurally valid coordinate is passed to CRForge.
    """
    action = action_from_mapping(raw_action, resolution=ActionResolution.tile_center())
    if isinstance(action, WaitAction):
        return int(schema.wait), True

    mask = np.asarray(action_mask, dtype=np.uint8)
    if isinstance(action, PlayAction):
        hand_ids = np.asarray(schema.field(raw_observation, "hand_card")).reshape(-1)
        hand_slot_card = int(hand_ids[action.hand_slot])
        actual_name = card_name_lookup(hand_slot_card)
        if actual_name is None:
            raise ValueError(
                f"CRForge observation has no card in hand slot {action.hand_slot}"
            )
        if actual_name != action.expected_card:
            raise ValueError(
                f"stale or mismatched hand slot {action.hand_slot}: expected "
                f"{action.expected_card!r}, current card is {actual_name!r}"
            )
        col = round(action.x_tile - 0.5)
        row = round(action.y_tile - 0.5)
        action_id = int(schema.play(action.hand_slot, col, row))
    elif isinstance(action, AbilityAction):
        action_id = int(schema.ability(action.button))
    else:
        raise TypeError(f"unsupported parsed action type: {type(action).__name__}")

    if action_id < 0 or action_id >= mask.size:
        raise ValueError(f"CRForge encoded action {action_id} is outside mask length {mask.size}")
    return action_id, bool(mask[action_id])
