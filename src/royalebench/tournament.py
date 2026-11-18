"""Paired round-robin tournaments and reproducible leaderboard export."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from royalebench.agents.base import Agent
from royalebench.ratings.glicko2 import PeriodGame, Rating, update_rating_period
from royalebench.runner import MatchResult, MatchRunner


AgentFactory = Callable[[], Agent]
EngineFactory = Callable[[int], Any]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned or "agent"


class TournamentRunner:
    """Runs every pair twice per seed, swapping seats for the second match."""

    def __init__(
        self,
        engine_factory: EngineFactory,
        *,
        profile: str,
        profile_ticks: int,
        request_timeout_s: float = 120.0,
    ) -> None:
        self.engine_factory = engine_factory
        self.profile = profile
        self.profile_ticks = int(profile_ticks)
        self.request_timeout_s = float(request_timeout_s)

    def run_round_robin(
        self,
        agent_factories: dict[str, AgentFactory],
        seeds: list[int],
        *,
        output_dir: str | Path,
        initial_rating: Rating = Rating(),
    ) -> dict[str, Any]:
        if len(agent_factories) < 2:
            raise ValueError("a round-robin tournament requires at least two agents")
        if not seeds:
            raise ValueError("at least one seed is required")
        if len(set(seeds)) != len(seeds):
            raise ValueError("tournament seeds must be unique")

        root = Path(output_dir)
        matches_dir = root / "matches"
        matches_dir.mkdir(parents=True, exist_ok=True)
        players = sorted(agent_factories)
        results: list[dict[str, Any]] = []
        completed: list[MatchResult] = []

        for left_index, left in enumerate(players):
            for right in players[left_index + 1 :]:
                for seed in seeds:
                    for left_seat in (0, 1):
                        ordered = (left, right) if left_seat == 0 else (right, left)
                        suffix = f"{_slug(left)}__{_slug(right)}__seed{seed}__{left_seat}"
                        match_id = f"{self.profile}__{suffix}"
                        engine = self.engine_factory(self.profile_ticks)
                        runner = MatchRunner(
                            engine,
                            profile=self.profile,
                            profile_ticks=self.profile_ticks,
                            request_timeout_s=self.request_timeout_s,
                        )
                        agents = (
                            agent_factories[ordered[0]](),
                            agent_factories[ordered[1]](),
                        )
                        if agents[0].name != ordered[0] or agents[1].name != ordered[1]:
                            for agent in agents:
                                try:
                                    agent.close()
                                except Exception:
                                    pass
                            try:
                                engine.close()
                            except Exception:
                                pass
                            raise ValueError(
                                "agent factory keys must match each created agent's .name"
                            )
                        result = runner.run(
                            agents,
                            seed=seed,
                            match_id=match_id,
                            output_dir=matches_dir / _slug(match_id),
                        )
                        row = result.to_dict()
                        row["pair"] = [left, right]
                        row["left_agent_seat"] = left_seat
                        results.append(row)
                        if result.status == "completed" and result.outcome in {
                            "draw",
                            "seat0_win",
                            "seat1_win",
                        }:
                            completed.append(result)

        period_games: dict[str, list[PeriodGame]] = defaultdict(list)
        for result in completed:
            seat0, seat1 = result.agents
            if seat0.endswith("@seat0") and seat1.endswith("@seat1"):
                # Self-play is not scheduled by round-robin, so this is only defensive.
                continue
            if result.outcome == "draw":
                score0 = 0.5
            else:
                score0 = 1.0 if result.winner == 0 else 0.0
            period_games[seat0].append(PeriodGame(seat1, score0))
            period_games[seat1].append(PeriodGame(seat0, 1.0 - score0))

        ratings = {name: initial_rating for name in players}
        ratings = update_rating_period(ratings, period_games)
        summary = {
            "schema": "royalebench.tournament-result.v1",
            "profile": self.profile,
            "decision_ticks": self.profile_ticks,
            "seeds": seeds,
            "agents": players,
            "total_matches": len(results),
            "completed_matches": len(completed),
            "void_or_failed_matches": len(results) - len(completed),
            "leaderboard": [
                {
                    "agent": name,
                    "rating": ratings[name].rating,
                    "rating_deviation": ratings[name].deviation,
                    "volatility": ratings[name].volatility,
                    "matches_rated": len(period_games.get(name, [])),
                }
                for name in sorted(players, key=lambda item: ratings[item].rating, reverse=True)
            ],
        }
        (root / "matches.json").write_text(
            json.dumps(results, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (root / "tournament.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (root / "leaderboard.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "rank",
                    "agent",
                    "rating",
                    "rating_deviation",
                    "volatility",
                    "matches_rated",
                ],
            )
            writer.writeheader()
            for rank, row in enumerate(summary["leaderboard"], start=1):
                writer.writerow({"rank": rank, **row})
        return summary
