"""Deterministic opponent card-cycle deductions from public play history."""

from __future__ import annotations

from typing import Any


CYCLE_LENGTH = 4


def derive_opponent_cycle(
    deck: list[str],
    recent_plays_newest_first: list[dict[str, Any]],
    *,
    play_count: int,
) -> dict[str, Any]:
    """Infer the opponent's hand set from the last four publicly shown card plays.

    A played card returns to a four-card hand after four subsequent card plays.
    The latest four distinct plays therefore identify the queue; the other four
    cards identify the current hand set. Hand ordering remains unknown.
    """
    if len(deck) != 8 or len(set(deck)) != 8:
        raise ValueError("opponent cycle inference requires eight distinct known deck cards")
    if play_count < 0:
        raise ValueError("play_count must be non-negative")

    visible = [
        str(row["card"])
        for row in recent_plays_newest_first
        if row.get("card") in deck and (int(row.get("flags", 0)) & 1)
    ][:CYCLE_LENGTH]

    exact = (
        play_count >= CYCLE_LENGTH
        and len(visible) == CYCLE_LENGTH
        and len(set(visible)) == CYCLE_LENGTH
    )
    if exact:
        queued_newest_first = visible
        queued_oldest_first = list(reversed(queued_newest_first))
        hand_cards = [card for card in deck if card not in set(queued_newest_first)]
        exact = len(hand_cards) == CYCLE_LENGTH

    if not exact:
        hand_cards = [card for card in deck if card not in set(visible)]
        queued_oldest_first = list(reversed(visible))

    plays_until_return = [
        {"card": card, "plays_until_return": CYCLE_LENGTH - age}
        for age, card in enumerate(visible)
    ]
    return {
        "hand_cards": hand_cards,
        "hand_exact": exact,
        "hand_order_known": False,
        "queue_oldest_to_newest": queued_oldest_first,
        "queue_complete": exact,
        "plays_until_return": plays_until_return,
        "public_plays_observed": int(play_count),
        "inference": "last-four-public-card-plays",
        "uncertainty": None if exact else "fewer-than-four-or-incomplete-visible-card-plays",
    }
