from __future__ import annotations

import pytest

from royalebench.protocol.actions import ActionResolution, PlayAction
from royalebench.protocol.responses import AgentResponse, ResponseMismatchError


REQUEST_ID = "req-0001"
DECISION_ID = 42
OBSERVATION_HASH = "a" * 64


def valid_response():
    return {
        "schema": "royalebench.agent-response.v1",
        "request_id": REQUEST_ID,
        "decision_id": DECISION_ID,
        "observation_hash": OBSERVATION_HASH,
        "action": {
            "schema": "royalebench.action.v1",
            "type": "play",
            "hand_slot": 1,
            "expected_card": "Cannon",
            "x_tile": 8.25,
            "y_tile": 17.75,
        },
    }


def test_accepts_matching_response():
    response = AgentResponse.from_mapping(
        valid_response(),
        expected_request_id=REQUEST_ID,
        expected_decision_id=DECISION_ID,
        expected_observation_hash=OBSERVATION_HASH,
        resolution=ActionResolution.half_tile(),
    )
    assert isinstance(response.action, PlayAction)
    assert response.action.expected_card == "Cannon"


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", "another-request"),
        ("decision_id", 41),
        ("observation_hash", "b" * 64),
    ],
)
def test_rejects_stale_or_mismatched_response(field, value):
    raw = valid_response()
    raw[field] = value
    with pytest.raises(ResponseMismatchError):
        AgentResponse.from_mapping(
            raw,
            expected_request_id=REQUEST_ID,
            expected_decision_id=DECISION_ID,
            expected_observation_hash=OBSERVATION_HASH,
            resolution=ActionResolution.half_tile(),
        )


def test_rejects_non_hex_observation_hash():
    raw = valid_response()
    raw["observation_hash"] = "z" * 64
    with pytest.raises(ResponseMismatchError):
        AgentResponse.from_mapping(
            raw,
            expected_request_id=REQUEST_ID,
            expected_decision_id=DECISION_ID,
            expected_observation_hash=OBSERVATION_HASH,
            resolution=ActionResolution.half_tile(),
        )
