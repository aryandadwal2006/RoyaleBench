from __future__ import annotations

from royalebench.public_memory import derive_opponent_cycle

DECK = [
    "Cannon", "Fireball", "HogRider", "IceGolem",
    "IceSpirit", "Musketeer", "Skeletons", "TheLog",
]


def rows(*cards):
    return [{"card": card, "card_shown": True} for card in cards]


def test_cycle_is_uncertain_before_four_public_card_plays():
    history = rows("Cannon", "Fireball")
    cycle = derive_opponent_cycle(DECK, history, play_count=2)
    assert cycle["hand_exact"] is False
    assert cycle["hand_cards"] is None
    assert cycle["queue_complete"] is False


def test_four_recent_distinct_plays_in_newest_first_order_identify_hand_set():
    history = rows("IceSpirit", "Musketeer", "Skeletons", "TheLog")
    cycle = derive_opponent_cycle(DECK, history, play_count=4)
    assert cycle["hand_exact"] is True
    assert set(cycle["hand_cards"]) == {"Cannon", "Fireball", "HogRider", "IceGolem"}
    assert cycle["queue_oldest_to_newest"] == [
        "TheLog", "Skeletons", "Musketeer", "IceSpirit"
    ]
    assert cycle["plays_until_return"] == [
        {"card": "TheLog", "plays_until_return": 1},
        {"card": "Skeletons", "plays_until_return": 2},
        {"card": "Musketeer", "plays_until_return": 3},
        {"card": "IceSpirit", "plays_until_return": 4},
    ]


def test_unshown_last_play_invalidates_exact_cycle_even_if_older_four_are_known():
    history = rows("Fireball", "TheLog", "Skeletons", "Musketeer", "IceSpirit")
    history[-1]["flags"] = 0
    history[-1]["card"] = None
    cycle = derive_opponent_cycle(DECK, history, play_count=5)
    assert cycle["hand_exact"] is False
    assert cycle["queue_oldest_to_newest"] is None


def test_trailing_unused_rows_are_not_counted_as_actual_plays():
    history = rows("TheLog", "Skeletons", "Musketeer", "IceSpirit")
    history += [{"card": None, "flags": 0}] * 4
    cycle = derive_opponent_cycle(DECK, history, play_count=4)
    assert cycle["hand_exact"] is True
    assert cycle["queue_oldest_to_newest"][0] == "TheLog"


def test_rejects_non_eight_card_deck():
    try:
        derive_opponent_cycle(DECK[:7], [], play_count=0)
    except ValueError as exc:
        assert "eight distinct" in str(exc)
    else:
        raise AssertionError("expected deck validation error")
