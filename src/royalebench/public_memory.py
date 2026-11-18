"""Deterministic opponent card-cycle deductions from public play history."""

from __future__ import annotations

from typing import Any

CYCLE_LENGTH = 4


def derive_opponent_cycle(
    deck: list[str],
    plays_oldest_first: list[dict[str, Any]],
    *,
    play_count: int,
) -> dict[str, Any]:
    """Infer the opponent's hand set from the last four publicly shown card plays.

    CRForge emits its bounded play ledger oldest-first. Unused rows trail the ledger,
    and an individual card identity may remain unknown until the game shows that play.
    The function therefore considers exactly the last four actual play rows and
    fails closed if any of them is not publicly identified.

    After four distinct cards have been played since a card last occupied the hand,
    the four most recently played cards form the draw queue in oldest-to-newest order.
    The other four deck cards form the current hand set; their hand-slot order is unknown.
    """
    if len(deck) != 8 or len(set(deck)) != 8:
        raise ValueError("opponent cycle inference requires eight distinct known deck cards")
    if play_count < 0:
        raise ValueError("play_count must be non-negative")

    ledger_size = min(play_count, len(plays_oldest_first))
    ledger = plays_oldest_first[:ledger_size]
    latest_four = ledger[-CYCLE_LENGTH:]
    exact = (
        play_count >= CYCLE_LENGTH
        and len(latest_four) == CYCLE_LENGTH
        and all(
            row.get("card") in deck and (int(row.get("flags", 0)) & 1) != 0
            for row in latest_four
        )
        and len({str(row["card"]) for row in latest_four}) == CYCLE_LENGTH
    )

    if exact:
        queue = [str(row["card"]) for row in latest_four]
        hand_cards: list[str] | None = [card for card in deck if card not in set(queue)]
        if len(hand_cards) != CYCLE_LENGTH:
            exact = False
            hand_cards = None
    else:
        queue = []
        hand_cards = None

    plays_until_return = (
        [
            {"card": card, "plays_until_return": index + 1}
            for index, card in enumerate(queue)
        ]
        if exact
        else []
    )
    uncertainty = (
        None
        if exact
        else "one-or-more-of-last-four-plays-is-not-publicly-identified"
    )
    return {
        "hand_cards": hand_cards,
        "hand_exact": exact,
        "hand_order_known": False,
        "queue_oldest_to_newest": queue if exact else None,
        "queue_complete": exact,
        "plays_until_return": plays_until_return,
        "public_plays_observed": int(play_count),
        "inference": "last-four-public-card-plays",
        "uncertainty": uncertainty,
    }
