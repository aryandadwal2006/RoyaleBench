from __future__ import annotations

import json

from royalebench.agents.openai_compatible import OpenAICompatibleAgent


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_openai_compatible_agent_sends_observation_and_parses_action(monkeypatch):
    action = {"schema": "royalebench.action.v1", "type": "wait"}
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode())
        seen["authorization"] = request.get_header("Authorization")
        return FakeResponse({
            "choices": [{"message": {"content": json.dumps(action)}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    agent = OpenAICompatibleAgent(
        model="test-model",
        base_url="https://example.invalid/v1",
        api_key="test-secret",
        timeout_s=7,
    )
    observation = {"schema": "royalebench.observation.v1", "own": {"elixir_scaled": 50000}}
    agent.reset({"match_id": "m1", "seed": 1, "seat": 0, "profile": "test"})
    assert agent.act(observation) == action
    assert seen["url"] == "https://example.invalid/v1/chat/completions"
    assert seen["timeout"] == 7
    assert seen["authorization"] == "Bearer test-secret"
    assert json.loads(seen["body"]["messages"][1]["content"]) == observation
    assert agent.last_telemetry["usage"]["prompt_tokens"] == 50


def test_agent_requires_model_and_key(monkeypatch):
    monkeypatch.delenv("ROYALEBENCH_LLM_MODEL", raising=False)
    monkeypatch.delenv("ROYALEBENCH_LLM_API_KEY", raising=False)
    try:
        OpenAICompatibleAgent(base_url="https://example.invalid/v1", api_key="key")
    except ValueError as exc:
        assert "ROYALEBENCH_LLM_MODEL" in str(exc)
    else:
        raise AssertionError("expected missing model failure")
