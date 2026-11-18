from __future__ import annotations

import json
from types import SimpleNamespace

from royalebench.tournament import TournamentRunner


class DrawAgent:
    def __init__(self, name):
        self.name = name

    def reset(self, match_info):
        self.seat = match_info["seat"]

    def act(self, observation):
        return {"schema": "royalebench.action.v1", "type": "wait"}

    def close(self):
        pass


class SeatZeroWinnerEngine:
    def __init__(self, ticks):
        self.config = SimpleNamespace(deck=("Cannon",), card_level=11, tower_level=11, max_ticks=9000, mask_version=1)
        self.metadata = {"fingerprint": "test"}
        self.tick = 0

    def reset(self, seed, *, match_id):
        self.seed = seed
        self.match_id = match_id
        self.tick = 0
        return self.observe(0), self.observe(1)

    def observe(self, seat):
        return {
            "schema": "royalebench.observation.v1",
            "match_id": self.match_id,
            "decision_id": self.tick,
            "seat": seat,
            "game": {"tick": self.tick},
            "own": {"hand": []},
            "opponent": {},
            "entities": [],
            "legal_actions": {"playable_slots": [], "ability_slots": []},
            "engine": {"fingerprint": "test"},
        }

    def encode_action(self, seat, action):
        return 0, True

    def step(self, actions):
        self.tick += 5
        return SimpleNamespace(
            done=True,
            info={
                "tick": self.tick,
                "winner": 0,
                "truncated": 0,
                "crowns_0": 1,
                "crowns_1": 0,
                "illegal_0": 0,
                "illegal_1": 0,
            },
            fault=None,
        )

    def close(self):
        pass


def test_round_robin_runs_paired_seat_swaps_and_reports_wdl_ci(tmp_path):
    factories = {
        "agent-a": lambda: DrawAgent("agent-a"),
        "agent-b": lambda: DrawAgent("agent-b"),
    }
    runner = TournamentRunner(
        lambda ticks: SeatZeroWinnerEngine(ticks),
        profile="test-profile",
        profile_ticks=5,
    )
    summary = runner.run_round_robin(factories, [1, 2, 3], output_dir=tmp_path)
    assert summary["total_matches"] == 6
    assert summary["completed_matches"] == 6
    rows = {row["agent"]: row for row in summary["leaderboard"]}
    assert rows["agent-a"]["wins"] == 3
    assert rows["agent-a"]["losses"] == 3
    assert rows["agent-b"]["wins"] == 3
    assert rows["agent-b"]["losses"] == 3
    assert rows["agent-a"]["score_ci95"] is not None
    assert rows["agent-b"]["score_ci95"] is not None
    assert (tmp_path / "leaderboard.csv").exists()
    match_rows = json.loads((tmp_path / "matches.json").read_text())
    assert {row["left_agent_seat"] for row in match_rows} == {0, 1}


def test_tournament_refuses_to_overwrite_existing_match_results(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    (matches / "old.json").write_text("{}")
    runner = TournamentRunner(
        lambda ticks: SeatZeroWinnerEngine(ticks),
        profile="test-profile",
        profile_ticks=5,
    )
    factories = {
        "agent-a": lambda: DrawAgent("agent-a"),
        "agent-b": lambda: DrawAgent("agent-b"),
    }
    try:
        runner.run_round_robin(factories, [1, 2, 3], output_dir=tmp_path)
    except FileExistsError as exc:
        assert "choose a new" in str(exc)
    else:
        raise AssertionError("expected output collision to be rejected")
