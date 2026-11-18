from __future__ import annotations

import gzip
import json
import time
from types import SimpleNamespace

from royalebench.agents.baselines import NoOpAgent
from royalebench.runner import MatchRunner


class FakeEngine:
    def __init__(self):
        self.config = SimpleNamespace(deck=("Cannon",) * 8)
        self.metadata = {"data_version": "fake"}
        self.tick = 0
        self.closed = False

    def reset(self, seed, *, match_id):
        del seed, match_id
        self.tick = 0
        return self.observe(0), self.observe(1)

    def observe(self, seat):
        return {
            "schema": "royalebench.observation.v1",
            "match_id": "test-match",
            "decision_id": self.tick,
            "seat": seat,
            "own": {"hand": [], "deck": [], "elixir_scaled": 50000},
            "opponent": {},
            "entities": [],
            "legal_actions": {"playable_slots": [], "ability_slots": []},
            "game": {"tick": self.tick},
            "engine": {"data_version": "fake"},
        }

    def encode_action(self, seat, action):
        assert action["type"] == "wait"
        return seat, True

    def step(self, actions):
        assert actions == [0, 1]
        self.tick += 5
        return SimpleNamespace(
            done=self.tick >= 10,
            info={
                "tick": self.tick,
                "winner": 2 if self.tick >= 10 else -1,
                "truncated": 0,
                "crowns_0": 1,
                "crowns_1": 1,
                "illegal_0": 0,
                "illegal_1": 0,
            },
            fault=None,
        )

    def close(self):
        self.closed = True


def test_runner_executes_both_seats_and_writes_trajectory(tmp_path):
    engine = FakeEngine()
    runner = MatchRunner(engine, profile="test", profile_ticks=5)
    result = runner.run(
        (NoOpAgent(), NoOpAgent()),
        seed=12,
        match_id="test-match",
        output_dir=tmp_path,
    )
    assert result.status == "completed"
    assert result.outcome == "draw"
    assert result.winner is None
    assert result.decisions == 2
    assert engine.closed
    assert (tmp_path / "manifest.json").exists()
    with gzip.open(tmp_path / "trajectory.jsonl.gz", "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    assert len(rows) == 4
    assert all("next_observation" in row for row in rows)



class MutatingAgent(NoOpAgent):
    name = "mutating-agent"

    def act(self, observation):
        observation["own"]["hand"].append({"slot": 99, "card": "Injected"})
        return {"schema": "royalebench.action.v1", "type": "wait"}


class DelayedAgent(NoOpAgent):
    name = "delayed-agent"

    def act(self, observation):
        time.sleep(0.02)
        return super().act(observation)


class InvalidAgent(NoOpAgent):
    name = "invalid-agent"

    def act(self, observation):
        return {"schema": "royalebench.action.v1", "type": "unknown"}


def test_runner_gives_agents_isolated_observation_copies(tmp_path):
    engine = FakeEngine()
    runner = MatchRunner(engine, profile="test", profile_ticks=5)
    result = runner.run(
        (MutatingAgent(), NoOpAgent()),
        seed=12,
        match_id="mutation-test",
        output_dir=tmp_path,
    )
    assert result.status == "completed"
    with gzip.open(tmp_path / "trajectory.jsonl.gz", "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    seat_zero = next(row for row in rows if row["seat"] == 0)
    assert seat_zero["observation"]["own"]["hand"] == []


def test_runner_uses_one_shared_deadline_for_both_concurrent_agents(tmp_path):
    engine = FakeEngine()
    runner = MatchRunner(
        engine,
        profile="test",
        profile_ticks=5,
        request_timeout_s=0.05,
    )
    result = runner.run(
        (DelayedAgent(), DelayedAgent()),
        seed=12,
        match_id="deadline-test",
        output_dir=tmp_path,
    )
    assert result.status == "completed"


def test_invalid_agent_action_is_classified_as_agent_error(tmp_path):
    engine = FakeEngine()
    runner = MatchRunner(engine, profile="test", profile_ticks=5)
    result = runner.run(
        (InvalidAgent(), NoOpAgent()),
        seed=12,
        match_id="invalid-test",
        output_dir=tmp_path,
    )
    assert result.status == "agent_error"
    assert result.outcome == "void"
    assert result.fault["kind"] == "agent_error"
