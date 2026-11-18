"""Minimal external RoyaleBench JSONL agent.

Run from the repository root:
    python examples/agents/hog_cycle_jsonl.py

The worker uses stdin/stdout only for the versioned protocol. Put diagnostics on stderr.
"""

from __future__ import annotations

import json
import sys
from typing import Any

EVENT_SCHEMA = "royalebench.agent-event.v1"
REQUEST_SCHEMA = "royalebench.agent-request.v1"
RESPONSE_SCHEMA = "royalebench.agent-response.v1"
ACTION_SCHEMA = "royalebench.action.v1"


def choose_action(observation: dict[str, Any]) -> dict[str, Any]:
    """A deliberately small Hog Rider policy demonstrating the external API."""
    own = observation["own"]
    legal = observation["legal_actions"]
    hand = own["hand"]

    for slot in legal["playable_slots"]:
        card = hand[slot]["card"]
        if card == "HogRider" and own["elixir"] >= hand[slot]["cost_elixir"]:
            left_hp = observation["opponent"]["towers"]["enemy_left"]["hp"]
            right_hp = observation["opponent"]["towers"]["enemy_right"]["hp"]
            lane_x = 3.5 if left_hp <= right_hp else 14.5
            return {
                "schema": ACTION_SCHEMA,
                "type": "play",
                "hand_slot": slot,
                "expected_card": card,
                "x_tile": lane_x,
                "y_tile": 14.5,
            }

    return {"schema": ACTION_SCHEMA, "type": "wait"}


def send(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), allow_nan=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            print("ignored malformed request JSON", file=sys.stderr)
            continue

        if not isinstance(message, dict):
            print("ignored non-object protocol message", file=sys.stderr)
            continue

        schema = message.get("schema")
        event_type = message.get("type")

        if schema == EVENT_SCHEMA and event_type == "start":
            # Initialize private recurrent state here. A fresh process is started per match.
            send({"schema": EVENT_SCHEMA, "type": "ready"})

        elif schema == REQUEST_SCHEMA and event_type == "act":
            observation = message.get("observation")
            if not isinstance(observation, dict):
                continue
            response = {
                "schema": RESPONSE_SCHEMA,
                "request_id": message["request_id"],
                "decision_id": message["decision_id"],
                "observation_hash": message["observation_hash"],
                "action": choose_action(observation),
            }
            send(response)

        elif schema == EVENT_SCHEMA and event_type == "end":
            # Persist match-level diagnostics here if needed. No response is expected.
            result = message.get("result", {})
            print(
                f"match {result.get('match_id')} ended: {result.get('outcome')}",
                file=sys.stderr,
            )

        elif schema == EVENT_SCHEMA and event_type == "close":
            break

        else:
            print(f"ignored unknown protocol message: {schema!r}/{event_type!r}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
