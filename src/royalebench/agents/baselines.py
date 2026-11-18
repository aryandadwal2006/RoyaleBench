"""Deterministic and stochastic baselines for protocol validation and play."""

from __future__ import annotations

from typing import Any

import numpy as np

ACTION_SCHEMA = "royalebench.action.v1"


def wait_action() -> dict[str, Any]:
    return {"schema": ACTION_SCHEMA, "type": "wait"}


def play_action(slot: int, card: str, x: float, y: float) -> dict[str, Any]:
    return {
        "schema": ACTION_SCHEMA,
        "type": "play",
        "hand_slot": int(slot),
        "expected_card": card,
        "x_tile": float(x),
        "y_tile": float(y),
    }


def ability_action(button: int) -> dict[str, Any]:
    return {"schema": ACTION_SCHEMA, "type": "ability", "button": int(button)}


class NoOpAgent:
    """Always waits. Useful for smoke tests, not a meaningful strategic opponent."""

    name = "noop-v1"

    def reset(self, match_info: dict[str, Any]) -> None:
        del match_info

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        del observation
        return wait_action()

    def close(self) -> None:
        return None


class RandomLegalAgent:
    """Uniformly samples an available play slot and a placement tile."""

    name = "random-legal-v1"

    def __init__(self, *, seed_offset: int = 0, wait_probability: float = 0.15) -> None:
        if not 0.0 <= wait_probability <= 1.0:
            raise ValueError("wait_probability must be between zero and one")
        self.seed_offset = int(seed_offset)
        self.wait_probability = float(wait_probability)
        self.rng = np.random.default_rng(0)

    def reset(self, match_info: dict[str, Any]) -> None:
        seed = int(match_info["seed"]) + self.seed_offset + 1009 * int(match_info["seat"])
        self.rng = np.random.default_rng(seed)

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        legal = observation["legal_actions"]
        if self.rng.random() < self.wait_probability:
            return wait_action()

        abilities = list(legal["ability_slots"])
        slots = list(legal["playable_slots"])
        if abilities and self.rng.random() < 0.02:
            return ability_action(int(self.rng.choice(abilities)))
        if not slots:
            return wait_action()

        slot = int(self.rng.choice(slots))
        card = observation["own"]["hand"][slot]["card"]
        if not card:
            return wait_action()
        col = int(self.rng.integers(0, 18))
        row = int(self.rng.integers(0, 32))
        return play_action(slot, card, col + 0.5, row + 0.5)

    def close(self) -> None:
        return None


class HogCycleAgent:
    """A small transparent Hog-cycle policy used as a non-learning baseline.

    Rules are intentionally simple: send Hog Rider at the bridge when available; defend a
    penetrating threat with Cannon, Musketeer or Ice Golem; otherwise cycle a cheap troop behind
    the king. This is a reference baseline, not a claim of strong Clash Royale play.
    """

    name = "hog-cycle-rules-v1"

    def reset(self, match_info: dict[str, Any]) -> None:
        del match_info

    @staticmethod
    def _normal(card: str | None) -> str:
        return "".join(ch for ch in (card or "").casefold() if ch.isalnum())

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        own = observation["own"]
        hand = own["hand"]
        slots = list(observation["legal_actions"]["playable_slots"])
        if not slots:
            return wait_action()

        def available(names: set[str]) -> list[int]:
            return [
                slot
                for slot in slots
                if self._normal(hand[slot]["card"]) in names
            ]

        hog = available({"hogrider"})
        if hog:
            left_hp = observation["opponent"]["towers"]["enemy_left"]["hp"]
            right_hp = observation["opponent"]["towers"]["enemy_right"]["hp"]
            lane_col = 3.5 if left_hp <= right_hp else 14.5
            slot = hog[0]
            return play_action(slot, hand[slot]["card"], lane_col, 14.5)

        threatened = any(
            entity.get("kind_name") == "character"
            and entity.get("side") == 1
            and "alive" in entity.get("flag_names", [])
            and 0.0 <= float(entity.get("y_tiles", 32.0)) < 15.0
            for entity in observation["entities"]
        )
        if threatened:
            defenders = available({"cannon", "musketeer", "icegolem"})
            if defenders:
                slot = min(defenders, key=lambda index: hand[index]["cost_elixir"])
                card = hand[slot]["card"]
                if self._normal(card) == "cannon":
                    return play_action(slot, card, 8.5, 9.5)
                return play_action(slot, card, 8.5, 5.5)

        cycle = available({"icespirit", "skeletons"})
        if cycle:
            slot = min(cycle, key=lambda index: hand[index]["cost_elixir"])
            return play_action(slot, hand[slot]["card"], 8.5, 3.5)

        return wait_action()

    def close(self) -> None:
        return None
