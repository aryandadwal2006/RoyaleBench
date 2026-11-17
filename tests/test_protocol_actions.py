import pytest

from royalebench.protocol.actions import (
    AbilityAction,
    ActionResolution,
    ActionValidationError,
    PlayAction,
    WaitAction,
    action_from_mapping,
)


def test_wait_action():
    action = action_from_mapping(
        {"schema": "royalebench.action.v1", "type": "wait"},
        resolution=ActionResolution.half_tile(),
    )
    assert isinstance(action, WaitAction)


def test_ability_action():
    action = action_from_mapping(
        {
            "schema": "royalebench.action.v1",
            "type": "ability",
            "button": 1,
        },
        resolution=ActionResolution.half_tile(),
    )
    assert action == AbilityAction(button=1)


def test_half_tile_play_action():
    action = action_from_mapping(
        {
            "schema": "royalebench.action.v1",
            "type": "play",
            "hand_slot": 2,
            "expected_card": "Fireball",
            "x_tile": 8.25,
            "y_tile": 17.75,
        },
        resolution=ActionResolution.half_tile(),
    )
    assert action == PlayAction(
        hand_slot=2,
        expected_card="Fireball",
        x_tile=8.25,
        y_tile=17.75,
    )


def test_tile_center_play_action():
    action = action_from_mapping(
        {
            "schema": "royalebench.action.v1",
            "type": "play",
            "hand_slot": 0,
            "expected_card": "Hog Rider",
            "x_tile": 8.5,
            "y_tile": 17.5,
        },
        resolution=ActionResolution.tile_center(),
    )
    assert isinstance(action, PlayAction)


@pytest.mark.parametrize(
    "x_tile,y_tile",
    [
        (8.5, 17.5),   # tile-centre is invalid in half-tile mode
        (8.0, 17.0),   # tile edge
        (-0.25, 1.25),
        (18.0, 1.25),
        (1.25, 32.0),
    ],
)
def test_rejects_coordinates_outside_half_tile_centres(x_tile, y_tile):
    raw = {
        "schema": "royalebench.action.v1",
        "type": "play",
        "hand_slot": 0,
        "expected_card": "Knight",
        "x_tile": x_tile,
        "y_tile": y_tile,
    }
    with pytest.raises(ActionValidationError):
        action_from_mapping(raw, resolution=ActionResolution.half_tile())


def test_rejects_wrong_card_slot_or_unknown_keys():
    raw = {
        "schema": "royalebench.action.v1",
        "type": "play",
        "hand_slot": 4,
        "expected_card": "Knight",
        "x_tile": 8.25,
        "y_tile": 17.75,
    }
    with pytest.raises(ActionValidationError):
        action_from_mapping(raw, resolution=ActionResolution.half_tile())

    raw["hand_slot"] = 0
    raw["hidden_opponent_elixir"] = 8
    with pytest.raises(ActionValidationError):
        action_from_mapping(raw, resolution=ActionResolution.half_tile())
