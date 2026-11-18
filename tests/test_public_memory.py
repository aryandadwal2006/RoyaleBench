from __future__ import annotations

from royalebench.public_memory import derive_opponent_cycle

DECK = [
    "Cannon", "Fireball", "HogRider", "IceGolem",
    "IceSpirit", "Musketeer", "Skeletons", "TheLog",
]


def rows(*cards):
    return [{"card": card, "flags": 1} for card in cards]


def test_cycle_is_uncertain_before_four_public_card_plays():
    cycle = derive_opponent_cycle(DECK, rows("Cannon", "Fireball"), play_count=2)
    assert cycle["hand_exact"] is False
    assert set(cycle["hand_cards"]) == set(DECK) - {"Cannon", "Fireball"}
    assert cycle["queue_complete"] is False


def test_four_recent_distinct_plays_identify_hand_set_and_queue():
    cycle = derive_opponent_cycle(
        DECK,
        rows("TheLog", "Skeletons", "Musketeer", "IceSpirit"),
        play_count=12,
    )
    assert cycle["hand_exact"] is True
    assert set(cycle["hand_cards"]) == {"Cannon", "Fireball", "HogRider", "IceGolem"}
    assert cycle["queue_oldest_to_newest"] == [
        "IceSpirit", "Musketeer", "Skeletons", "TheLog"
    ]
    assert cycle["plays_until_return"][0] == {
        "card": "TheLog",
        "plays_until_return": 4,
    }
    assert cycle["plays_until_return"][-1] == {
        "card": "IceSpirit",
        "plays_until_return": 1,
    }


def test_hidden_recent_plays_do_not_become_exact():
    history = rows("TheLog", "Skeletons", "Musketeer", "IceSpirit")
    history[1]["flags"] = 0
    cycle = derive_opponent_cycle(DECK, history, play_count=8)
    assert cycle["hand_exact"] is False
    assert cycle["uncertainty"] is not None


def test_rejects_non_eight_card_deck():
    try:
        derive_opponent_cycle(DECK[:7], [], play_count=0)
    except ValueError as exc:
        assert "eight distinct" in str(exc)
    else:
        raise AssertionError("expected deck validation error")
