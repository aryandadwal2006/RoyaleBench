"""Paired round-robin tournaments and reproducible leaderboard export."""

from __future__ import annotations

import csv
import json
import random
import re
import statistics
from collections import defaultdict
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from royalebench.agents.base import Agent
from royalebench.ratings.glicko2 import PeriodGame, Rating, update_rating_period
from royalebench.runner import MatchResult, MatchRunner

AgentFactory = Callable[[], Agent]
EngineFactory = Callable[[int], Any]
_BOOTSTRAP_ITERATIONS = 10_000


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned or "agent"


def _cluster_bootstrap_ci(
    seed_scores: dict[int, list[float]],
    *,
    rng_seed: int,
    iterations: int = _BOOTSTRAP_ITERATIONS,
) -> list[float] | None:
    """Percentile CI over simulator-seed clusters, preserving side-swapped pairing."""
    cluster_means = [
        statistics.fmean(scores) for _, scores in sorted(seed_scores.items()) if scores
    ]
    if len(cluster_means) < 2:
        return None
    rng = random.Random(rng_seed)
    estimates = []
    for _ in range(iterations):
        sample = [rng.choice(cluster_means) for _ in cluster_means]
        estimates.append(statistics.fmean(sample))
    estimates.sort()
    lower = estimates[int(0.025 * (iterations - 1))]
    upper = estimates[int(0.975 * (iterations - 1))]
    return [lower, upper]


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
        initial_rating: Rating | None = None,
    ) -> dict[str, Any]:
        if len(agent_factories) < 2:
            raise ValueError("a round-robin tournament requires at least two agents")
        if not seeds:
            raise ValueError("at least one seed is required")
        if len(set(seeds)) != len(seeds):
            raise ValueError("tournament seeds must be unique")
        if any(not -(2**31) <= int(seed) < 2**31 for seed in seeds):
            raise ValueError("all seeds must fit CRForge's signed 32-bit seed field")

        players = sorted(agent_factories)
        slugs = [_slug(player) for player in players]
        if len(set(slugs)) != len(slugs):
            raise ValueError("agent names collide after conversion to filesystem-safe match IDs")

        root = Path(output_dir)
        matches_dir = root / "matches"
        if matches_dir.exists() and any(matches_dir.iterdir()):
            raise FileExistsError(
                f"{matches_dir} already contains matches; choose a new tournament output directory"
            )
        matches_dir.mkdir(parents=True, exist_ok=True)

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
                                with suppress(Exception):
                                    agent.close()
                            with suppress(Exception):
                                engine.close()
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
        seed_scores: dict[str, dict[int, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        counts = {
            name: {"wins": 0, "draws": 0, "losses": 0} for name in players
        }
        for result in completed:
            names = result.agents
            if result.outcome == "draw":
                seat_scores = (0.5, 0.5)
                counts[names[0]]["draws"] += 1
                counts[names[1]]["draws"] += 1
            else:
                winning_seat = int(result.winner)
                losing_seat = 1 - winning_seat
                seat_scores = (1.0, 0.0) if winning_seat == 0 else (0.0, 1.0)
                counts[names[winning_seat]]["wins"] += 1
                counts[names[losing_seat]]["losses"] += 1

            for seat, name in enumerate(names):
                score = seat_scores[seat]
                period_games[name].append(PeriodGame(names[1 - seat], score))
                seed_scores[name][result.seed].append(score)

        starting_rating = initial_rating if initial_rating is not None else Rating()
        ratings = {name: starting_rating for name in players}
        ratings = update_rating_period(ratings, period_games)

        leaderboard = []
        for name in players:
            per_seed_scores = [
                statistics.fmean(scores)
                for _, scores in sorted(seed_scores[name].items())
                if scores
            ]
            mean_score = statistics.fmean(per_seed_scores) if per_seed_scores else 0.5
            interval = _cluster_bootstrap_ci(
                seed_scores[name],
                rng_seed=sum(name.encode()) + sum(int(seed) for seed in seeds),
            )
            win_draw_loss = counts[name]
            leaderboard.append(
                {
                    "agent": name,
                    "rating": ratings[name].rating,
                    "rating_deviation": ratings[name].deviation,
                    "volatility": ratings[name].volatility,
                    "matches_rated": sum(win_draw_loss.values()),
                    "wins": win_draw_loss["wins"],
                    "draws": win_draw_loss["draws"],
                    "losses": win_draw_loss["losses"],
                    "score": mean_score,
                    "score_ci95": interval,
                    "score_ci_method": (
                        "10,000-replicate percentile bootstrap over simulator-seed clusters"
                    ),
                }
            )
        leaderboard.sort(key=lambda row: row["rating"], reverse=True)
        for rank, row in enumerate(leaderboard, start=1):
            row["rank"] = rank

        summary = {
            "schema": "royalebench.tournament-result.v1",
            "profile": self.profile,
            "decision_ticks": self.profile_ticks,
            "seeds": seeds,
            "agents": players,
            "total_matches": len(results),
            "completed_matches": len(completed),
            "void_or_failed_matches": len(results) - len(completed),
            "leaderboard": leaderboard,
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
                    "wins",
                    "draws",
                    "losses",
                    "score",
                    "score_ci95",
                ],
            )
            writer.writeheader()
            for row in leaderboard:
                csv_row = dict(row)
                csv_row["score_ci95"] = json.dumps(row["score_ci95"])
                writer.writerow(csv_row)
        return summary
