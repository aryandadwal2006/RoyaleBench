from __future__ import annotations

import sys

import pytest

from royalebench.agents.subprocess_agent import AgentProcessError, JsonlSubprocessAgent

WAIT = {"schema": "royalebench.action.v1", "type": "wait"}


def observation() -> dict:
    return {
        "schema": "royalebench.observation.v1",
        "match_id": "subprocess-match",
        "decision_id": 0,
        "seat": 0,
    }


def test_jsonl_subprocess_agent_round_trip_and_telemetry():
    child = r"""
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    if request["type"] == "act":
        print(json.dumps({
            "request_id": request["request_id"],
            "decision_id": request["decision_id"],
            "observation_hash": request["observation_hash"],
            "action": {"schema": "royalebench.action.v1", "type": "wait"},
            "telemetry": {"policy": "test-worker"}
        }), flush=True)
    elif request["type"] == "close":
        break
"""
    agent = JsonlSubprocessAgent(
        "jsonl-test",
        [sys.executable, "-u", "-c", child],
        timeout_s=2.0,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    try:
        assert agent.act(observation()) == WAIT
        assert agent.last_telemetry == {"policy": "test-worker"}
    finally:
        agent.close()


def test_jsonl_subprocess_agent_enforces_timeout_and_terminates_child():
    child = r"""
import json
import sys
import time

for line in sys.stdin:
    request = json.loads(line)
    if request["type"] == "act":
        time.sleep(10)
    elif request["type"] == "close":
        break
"""
    agent = JsonlSubprocessAgent(
        "sleeping-test",
        [sys.executable, "-u", "-c", child],
        timeout_s=0.05,
        shutdown_timeout_s=0.1,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    with pytest.raises(TimeoutError, match="response deadline"):
        agent.act(observation())
    assert agent._process is None
    agent.close()


def test_jsonl_subprocess_agent_rejects_stale_response():
    child = r"""
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    if request["type"] == "act":
        print(json.dumps({
            "request_id": "stale-request",
            "decision_id": request["decision_id"],
            "observation_hash": request["observation_hash"],
            "action": {"schema": "royalebench.action.v1", "type": "wait"}
        }), flush=True)
    elif request["type"] == "close":
        break
"""
    agent = JsonlSubprocessAgent(
        "stale-test",
        [sys.executable, "-u", "-c", child],
        timeout_s=2.0,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    try:
        with pytest.raises(AgentProcessError, match="request_id"):
            agent.act(observation())
    finally:
        agent.close()
