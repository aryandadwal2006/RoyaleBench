from __future__ import annotations

import json
import sys

import pytest

from royalebench.agents.subprocess_agent import SubprocessAgent

WAIT = {"schema": "royalebench.action.v1", "type": "wait"}


def _worker_body(action_block: str) -> str:
    return (
        "import json, sys\n"
        "for line in sys.stdin:\n"
        "    request = json.loads(line)\n"
        "    kind = request.get('type')\n"
        "    if kind == 'start':\n"
        "        print(json.dumps({'schema': 'royalebench.agent-event.v1', " 
        "'type': 'ready'}), flush=True)\n"
        "    elif kind == 'act':\n"
        + "\n".join("        " + line for line in action_block.splitlines())
        + "\n    elif kind == 'close':\n"
        "        break\n"
    )


def observation() -> dict:
    return {
        "schema": "royalebench.observation.v1",
        "match_id": "subprocess-match",
        "decision_id": 0,
        "seat": 0,
    }


def test_subprocess_agent_round_trip_and_secret_filtering(monkeypatch):
    monkeypatch.setenv("ROYALEBENCH_TEST_PARENT_SECRET", "must-not-be-inherited")
    action_block = """
print(json.dumps({
    'schema': 'royalebench.agent-response.v1',
    'request_id': request['request_id'],
    'decision_id': request['decision_id'],
    'observation_hash': request['observation_hash'],
    'action': {'schema': 'royalebench.action.v1', 'type': 'wait'},
    'telemetry': {
        'parent_secret_inherited':
            __import__('os').environ.get('ROYALEBENCH_TEST_PARENT_SECRET') is not None
    }
}), flush=True)
"""
    agent = SubprocessAgent(
        "jsonl-test",
        [sys.executable, "-u", "-c", _worker_body(action_block)],
        timeout_s=2.0,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    try:
        assert agent.act(observation()) == WAIT
        assert agent.last_telemetry == {"parent_secret_inherited": False}
    finally:
        agent.close()


def test_subprocess_agent_enforces_timeout_and_terminates_child():
    agent = SubprocessAgent(
        "sleeping-test",
        [sys.executable, "-u", "-c", _worker_body("import time\ntime.sleep(10)")],
        timeout_s=0.05,
        shutdown_timeout_s=0.1,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    with pytest.raises(TimeoutError, match="response timeout"):
        agent.act(observation())
    assert agent._process is None
    agent.close()


def test_subprocess_agent_rejects_stale_response():
    action_block = """
print(json.dumps({
    'schema': 'royalebench.agent-response.v1',
    'request_id': 'stale-request',
    'decision_id': request['decision_id'],
    'observation_hash': request['observation_hash'],
    'action': {'schema': 'royalebench.action.v1', 'type': 'wait'}
}), flush=True)
"""
    agent = SubprocessAgent(
        "stale-test",
        [sys.executable, "-u", "-c", _worker_body(action_block)],
        timeout_s=2.0,
    )
    agent.reset({"match_id": "subprocess-match", "seat": 0})
    try:
        with pytest.raises(ValueError, match="request_id"):
            agent.act(observation())
    finally:
        agent.close()


def test_subprocess_agent_requires_startup_handshake():
    agent = SubprocessAgent(
        "no-handshake",
        [sys.executable, "-u", "-c", "import time; time.sleep(10)"],
        startup_timeout_s=0.05,
        shutdown_timeout_s=0.1,
    )
    with pytest.raises(TimeoutError, match="response timeout"):
        agent.reset({"match_id": "subprocess-match", "seat": 0})
    assert agent._process is None


def test_subprocess_agent_receives_match_end_event(tmp_path):
    result_path = tmp_path / "end-result.json"
    worker = f"""
import json, sys
result_path = {str(result_path)!r}
for line in sys.stdin:
    request = json.loads(line)
    if request.get('type') == 'start':
        print(json.dumps({{'schema':'royalebench.agent-event.v1','type':'ready'}}), flush=True)
    elif request.get('type') == 'end':
        with open(result_path, 'w', encoding='utf-8') as handle:
            json.dump(request['result'], handle)
    elif request.get('type') == 'close':
        break
"""
    agent = SubprocessAgent("end-event-test", [sys.executable, "-u", "-c", worker])
    agent.reset({"match_id": "end-match", "seat": 1})
    agent.finish({"match_id": "end-match", "outcome": "draw", "status": "completed"})
    agent.close()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "draw"
    assert payload["status"] == "completed"
    assert payload["seat"] == 1
    assert payload["agent"] == "end-event-test"
