"""Request-bound agent response envelopes.

Request identity prevents a delayed or duplicated response from being applied
to a different game observation. Real-time scheduling performs a second
current-state check, including expected_card-in-hand-slot for play actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .actions import Action, ActionResolution, action_from_mapping


RESPONSE_SCHEMA = "royalebench.agent-response.v1"
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class ResponseMismatchError(ValueError):
    """An agent response does not belong to the outstanding request."""


@dataclass(frozen=True, slots=True)
class AgentResponse:
    request_id: str
    decision_id: int
    observation_hash: str
    action: Action
    telemetry: dict[str, Any] | None = None

    @classmethod
    def from_mapping(
        cls,
        raw: object,
        *,
        expected_request_id: str,
        expected_decision_id: int,
        expected_observation_hash: str,
        resolution: ActionResolution,
    ) -> AgentResponse:
        if not isinstance(raw, dict):
            raise ResponseMismatchError("agent response must be a JSON object")

        expected_keys = {
            "schema",
            "request_id",
            "decision_id",
            "observation_hash",
            "action",
        }
        allowed_keys = expected_keys | {"telemetry"}
        actual_keys = set(raw)
        if expected_keys - actual_keys:
            raise ResponseMismatchError(
                f"missing response keys: {sorted(expected_keys - actual_keys)}"
            )
        if actual_keys - allowed_keys:
            raise ResponseMismatchError(
                f"unexpected response keys: {sorted(actual_keys - allowed_keys)}"
            )
        if raw["schema"] != RESPONSE_SCHEMA:
            raise ResponseMismatchError("unsupported agent response schema")

        request_id = raw["request_id"]
        decision_id = raw["decision_id"]
        observation_hash = raw["observation_hash"]

        if request_id != expected_request_id:
            raise ResponseMismatchError("response request_id does not match")
        if (
            isinstance(decision_id, bool)
            or not isinstance(decision_id, int)
            or decision_id != expected_decision_id
        ):
            raise ResponseMismatchError("response decision_id does not match")
        if (
            not isinstance(observation_hash, str)
            or not _SHA256_RE.fullmatch(observation_hash)
            or observation_hash != expected_observation_hash
        ):
            raise ResponseMismatchError("response observation_hash does not match")

        telemetry = raw.get("telemetry")
        if telemetry is not None and not isinstance(telemetry, dict):
            raise ResponseMismatchError("telemetry must be an object when present")

        action = action_from_mapping(raw["action"], resolution=resolution)
        return cls(
            request_id=request_id,
            decision_id=decision_id,
            observation_hash=observation_hash,
            action=action,
            telemetry=telemetry,
        )
