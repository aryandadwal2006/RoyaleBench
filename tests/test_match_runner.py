from __future__ import annotations

import gzip
import json
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
