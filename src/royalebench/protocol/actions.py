"""Typed v1 actions and action-resolution validation.

The JSON Schema validates the wire shape. ActionResolution validates whether
the chosen coordinates belong to the quantized action grid declared by a match.
It never snaps or repairs an agent action.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import TypeAlias


ACTION_SCHEMA = "royalebench.action.v1"
ARENA_WIDTH_TILES = 18
ARENA_HEIGHT_TILES = 32
HAND_SLOTS = 4
ABILITY_BUTTONS = 2


class ActionValidationError(ValueError):
    """An agent response is malformed or incompatible with the match contract."""


@dataclass(frozen=True, slots=True)
class WaitAction:
    schema: str = ACTION_SCHEMA
    type: str = "wait"


@dataclass(frozen=True, slots=True)
class PlayAction:
    hand_slot: int
    expected_card: str
    x_tile: float
    y_tile: float
    schema: str = ACTION_SCHEMA
    type: str = "play"


@dataclass(frozen=True, slots=True)
class AbilityAction:
    button: int
    schema: str = ACTION_SCHEMA
    type: str = "ability"


Action: TypeAlias = WaitAction | PlayAction | AbilityAction


@dataclass(frozen=True, slots=True)
class ActionResolution:
    """Coordinate quantization used by a benchmark match.

    Coordinates are expressed in tile units in the acting seat's frame.
    The half-tile grid uses the centres of 0.5 x 0.5 tile cells, hence 0.25,
    0.75, ..., 17.75 on x and 0.25, 0.75, ..., 31.75 on y.
    """

    resolution_id: str
    offset_tiles: float
    step_tiles: float

    @classmethod
    def tile_center(cls) -> ActionResolution:
        return cls("tile-center-v1", offset_tiles=0.5, step_tiles=1.0)

    @classmethod
    def half_tile(cls) -> ActionResolution:
        return cls("half-tile-v1", offset_tiles=0.25, step_tiles=0.5)

    def validate_point(self, x_tile: float, y_tile: float) -> None:
        _validate_coordinate(
            x_tile,
            limit=ARENA_WIDTH_TILES,
            offset=self.offset_tiles,
            step=self.step_tiles,
            axis="x",
            resolution_id=self.resolution_id,
        )
        _validate_coordinate(
            y_tile,
            limit=ARENA_HEIGHT_TILES,
            offset=self.offset_tiles,
            step=self.step_tiles,
            axis="y",
            resolution_id=self.resolution_id,
        )


def _validate_coordinate(
    value: float,
    *,
    limit: int,
    offset: float,
    step: float,
    axis: str,
    resolution_id: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionValidationError(f"{axis}_tile must be a finite number")
    coordinate = float(value)
    if not 0.0 <= coordinate < float(limit):
        raise ActionValidationError(
            f"{axis}_tile={coordinate} is outside [0, {limit})"
        )
    if not ((coordinate - offset) / step >= -1e-8):
        raise ActionValidationError(
            f"{axis}_tile={coordinate} is not on {resolution_id}"
        )
    grid_position = (coordinate - offset) / step
    if not isclose(grid_position, round(grid_position), rel_tol=0.0, abs_tol=1e-7):
        raise ActionValidationError(
            f"{axis}_tile={coordinate} is not on {resolution_id}"
        )


def action_from_mapping(
    raw: object,
    *,
    resolution: ActionResolution,
) -> Action:
    """Parse and validate a JSON-like object under the v1 action contract.

    Coordinates are checked against the match resolution. No snapping, card
    substitution, legality repair or strategic fallback is performed here.
    """
    if not isinstance(raw, dict):
        raise ActionValidationError("action must be a JSON object")

    schema = raw.get("schema")
    action_type = raw.get("type")
    if schema != ACTION_SCHEMA:
        raise ActionValidationError(
            f"unsupported action schema {schema!r}; expected {ACTION_SCHEMA!r}"
        )

    if action_type == "wait":
        _require_exact_keys(raw, {"schema", "type"})
        return WaitAction()

    if action_type == "play":
        _require_exact_keys(
            raw,
            {"schema", "type", "hand_slot", "expected_card", "x_tile", "y_tile"},
        )
        hand_slot = raw["hand_slot"]
        if isinstance(hand_slot, bool) or not isinstance(hand_slot, int):
            raise ActionValidationError("hand_slot must be an integer")
        if not 0 <= hand_slot < HAND_SLOTS:
            raise ActionValidationError(f"hand_slot must be in [0, {HAND_SLOTS})")

        expected_card = raw["expected_card"]
        if not isinstance(expected_card, str) or not expected_card.strip():
            raise ActionValidationError("expected_card must be a non-empty card name")

        x_tile = _finite_number(raw["x_tile"], field="x_tile")
        y_tile = _finite_number(raw["y_tile"], field="y_tile")
        resolution.validate_point(x_tile, y_tile)

        return PlayAction(
            hand_slot=hand_slot,
            expected_card=expected_card,
            x_tile=x_tile,
            y_tile=y_tile,
        )

    if action_type == "ability":
        _require_exact_keys(raw, {"schema", "type", "button"})
        button = raw["button"]
        if isinstance(button, bool) or not isinstance(button, int):
            raise ActionValidationError("button must be an integer")
        if not 0 <= button < ABILITY_BUTTONS:
            raise ActionValidationError(
                f"button must be in [0, {ABILITY_BUTTONS})"
            )
        return AbilityAction(button=button)

    raise ActionValidationError(f"unsupported action type: {action_type!r}")


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionValidationError(f"{field} must be a finite number")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ActionValidationError(f"{field} must be a finite number")
    return number


def _require_exact_keys(raw: dict[str, object], expected: set[str]) -> None:
    actual = set(raw)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        if extra:
            details.append(f"unexpected keys: {sorted(extra)}")
        raise ActionValidationError("; ".join(details))
