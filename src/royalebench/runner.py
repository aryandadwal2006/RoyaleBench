"""Concurrent two-seat match execution and trajectory logging."""

from __future__ import annotations

import contextlib
import copy
import gzip
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from royalebench.agents.base import Agent
from royalebench.observations import OBSERVATION_SCHEMA, observation_hash
from royalebench.protocol.actions import ActionResolution
from royalebench.protocol.responses import RESPONSE_SCHEMA, AgentResponse


@dataclass(frozen=True, slots=True)
class MatchResult:
    match_id: str
    status: str
    outcome: str
    seed: int
    winner: int | None
    crowns: tuple[int, int]
    tick: int
    decisions: int
    agents: tuple[str, str]
    latency_ms: dict[str, dict[str, float]]
    invalid_actions: tuple[int, int]
    fault: dict[str, Any] | None = None
    output_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentExecutionError(RuntimeError):
    """An agent raised an exception or returned an invalid response."""


class MatchRunner:
    """Runs two agents on identical simulated decision ticks."""

    def __init__(
        self,
        engine: Any,
        *,
        profile: str,
        profile_ticks: int,
        request_timeout_s: float = 120.0,
        max_decisions: int = 20_000,
    ) -> None:
        if profile_ticks < 1:
            raise ValueError("profile_ticks must be positive")
        if request_timeout_s <= 0:
            raise ValueError("request_timeout_s must be positive")
        if max_decisions < 1:
            raise ValueError("max_decisions must be positive")
        self.engine = engine
        self.profile = profile
        self.profile_ticks = int(profile_ticks)
        self.request_timeout_s = float(request_timeout_s)
        self.max_decisions = int(max_decisions)

    @staticmethod
    def _call_agent(agent: Agent, observation: dict[str, Any]) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        action = agent.act(observation)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not isinstance(action, dict):
            raise AgentExecutionError(
                f"{agent.name} returned {type(action).__name__}; expected an ActionV1 object"
            )
        return action, elapsed_ms

    @staticmethod
    def _latency_summary(samples: list[float]) -> dict[str, float]:
        if not samples:
            return {"count": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
        ordered = sorted(samples)

        def percentile(p: float) -> float:
            index = min(int(round((len(ordered) - 1) * p)), len(ordered) - 1)
            return float(ordered[index])

        return {
            "count": float(len(samples)),
            "mean": float(statistics.fmean(samples)),
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        }

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def run(
        self,
        agents: tuple[Agent, Agent],
        *,
        seed: int,
        match_id: str,
        output_dir: str | Path | None = None,
    ) -> MatchResult:
        if len(agents) != 2:
            raise ValueError("a match needs exactly two agents")
        if agents[0].name == agents[1].name:
            names = (f"{agents[0].name}@seat0", f"{agents[1].name}@seat1")
        else:
            names = (agents[0].name, agents[1].name)

        destination = Path(output_dir) if output_dir is not None else None
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=True)

        latencies: dict[int, list[float]] = {0: [], 1: []}
        illegal_counts = [0, 0]
        decision_count = 0
        status = "agent_error"
        outcome = "undetermined"
        winner: int | None = None
        crowns = (0, 0)
        tick = 0
        fault: dict[str, Any] | None = None
        trajectory_path = destination / "trajectory.jsonl.gz" if destination else None

        manifest = {
            "schema": "royalebench.match-manifest.v1",
            "match_id": match_id,
            "seed": int(seed),
            "profile": self.profile,
            "decision_ticks": self.profile_ticks,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "observation_schema": OBSERVATION_SCHEMA,
            "response_schema": RESPONSE_SCHEMA,
            "action_resolution": ActionResolution.tile_center().resolution_id,
            "public_memory_version": "opponent-cycle-v1",
            "upstream": {
                "crforge_commit": "fa5959055c590a493d62c8dbc804e602832d08a6"
            },
            "match_config": {
                "deck": list(self.engine.config.deck),
                "card_level": self.engine.config.card_level,
                "tower_level": self.engine.config.tower_level,
                "max_ticks": self.engine.config.max_ticks,
                "mask_version": self.engine.config.mask_version,
            },
            "engine": self.engine.metadata,
            "agents": [{"name": agent.name, "seat": seat} for seat, agent in enumerate(agents)],
        }
        if destination is not None:
            self._write_json(destination / "manifest.json", manifest)

        try:
            reset_info = {
                "match_id": match_id,
                "seed": int(seed),
                "profile": self.profile,
                "decision_ticks": self.profile_ticks,
                "deck": list(self.engine.config.deck),
                "engine": self.engine.metadata,
            }
            for seat, agent in enumerate(agents):
                set_timeout = getattr(agent, "set_timeout", None)
                configured_timeout = getattr(agent, "timeout_s", self.request_timeout_s)
                if callable(set_timeout):
                    set_timeout(min(float(configured_timeout), self.request_timeout_s))
                agent.reset({**reset_info, "seat": seat})

            observations = self.engine.reset(seed, match_id=match_id)
            status = "completed"

            with (
                ThreadPoolExecutor(max_workers=2, thread_name_prefix="royalebench-agent") as pool,
                (
                    gzip.open(trajectory_path, "wt", encoding="utf-8")
                    if trajectory_path is not None
                    else _null_writer()
                ) as log,
            ):
                for decision_id in range(self.max_decisions):
                    futures = [
                        pool.submit(self._call_agent, agent, copy.deepcopy(observations[seat]))
                        for seat, agent in enumerate(agents)
                    ]
                    _, pending_futures = wait(futures, timeout=self.request_timeout_s)
                    if pending_futures:
                        timed_out_seats = [
                            seat for seat, future in enumerate(futures) if future in pending_futures
                        ]
                        labels = ", ".join(
                            f"{agents[seat].name}@seat{seat}" for seat in timed_out_seats
                        )
                        raise AgentExecutionError(
                            f"request watchdog expired after {self.request_timeout_s:.3f}s "
                            f"at decision {decision_id}: {labels}"
                        )

                    action_ids = [0, 0]
                    decision_records: list[dict[str, Any]] = []
                    for seat, future in enumerate(futures):
                        try:
                            raw_action, latency_ms = future.result()
                        except Exception as exc:
                            raise AgentExecutionError(
                                f"agent {agents[seat].name} at seat {seat}, decision "
                                f"{decision_id} failed: {exc}"
                            ) from exc

                        latencies[seat].append(latency_ms)
                        obs = observations[seat]
                        obs_hash = observation_hash(obs)
                        request_id = f"{match_id}:{decision_id}:{seat}"
                        telemetry = getattr(agents[seat], "last_telemetry", None)
                        envelope = {
                            "schema": RESPONSE_SCHEMA,
                            "request_id": request_id,
                            "decision_id": decision_id,
                            "observation_hash": obs_hash,
                            "action": raw_action,
                        }
                        if isinstance(telemetry, dict):
                            envelope["telemetry"] = telemetry
                        try:
                            parsed = AgentResponse.from_mapping(
                                envelope,
                                expected_request_id=request_id,
                                expected_decision_id=decision_id,
                                expected_observation_hash=obs_hash,
                                resolution=ActionResolution.tile_center(),
                            )
                            encoded, mask_open = self.engine.encode_action(seat, raw_action)
                        except Exception as exc:
                            raise AgentExecutionError(
                                f"agent {agents[seat].name} returned an invalid action at "
                                f"seat {seat}, decision {decision_id}: {exc}"
                            ) from exc
                        action_ids[seat] = encoded
                        decision_records.append(
                            {
                                "seat": seat,
                                "agent": agents[seat].name,
                                "observation": obs,
                                "observation_hash": obs_hash,
                                "response": envelope,
                                "validated_action": parsed.action.type,
                                "engine_action": encoded,
                                "mask_open": mask_open,
                                "latency_ms": latency_ms,
                            }
                        )

                    step = self.engine.step(action_ids)
                    decision_count += 1
                    tick = int(step.info.get("tick", tick))
                    illegal_counts[0] += int(step.info.get("illegal_0", 0))
                    illegal_counts[1] += int(step.info.get("illegal_1", 0))

                    next_observations = (self.engine.observe(0), self.engine.observe(1))
                    if log is not None:
                        for record in decision_records:
                            seat = record["seat"]
                            transition = {
                                **record,
                                "next_observation": next_observations[seat],
                                "next_observation_hash": observation_hash(next_observations[seat]),
                                "match_done": step.done,
                                "engine_tick": tick,
                            }
                            log.write(
                                json.dumps(transition, separators=(",", ":"), ensure_ascii=False)
                            )
                            log.write("\n")

                    observations = next_observations
                    if step.fault is not None:
                        status = "engine_fault"
                        outcome = "void"
                        fault = step.fault
                        break
                    if step.done:
                        if bool(step.info.get("truncated", 0)):
                            status = "truncated"
                            outcome = "void"
                        else:
                            status = "completed"
                            raw_winner = int(step.info.get("winner", -1))
                            if raw_winner in (0, 1):
                                winner = raw_winner
                                outcome = f"seat{raw_winner}_win"
                            elif raw_winner == 2:
                                outcome = "draw"
                            else:
                                status = "invalid_engine_result"
                                outcome = "void"
                        crowns = (
                            int(step.info.get("crowns_0", 0)),
                            int(step.info.get("crowns_1", 0)),
                        )
                        tick = int(step.info.get("tick", tick))
                        break
                else:
                    status = "decision_limit"
                    outcome = "void"

        except AgentExecutionError as exc:
            status = "agent_error"
            outcome = "void"
            fault = {"kind": "agent_error", "message": str(exc)}
        except Exception as exc:
            status = "runner_error"
            outcome = "void"
            fault = {"kind": "runner_error", "exception": type(exc).__name__, "message": str(exc)}
        finally:
            for agent in agents:
                with contextlib.suppress(Exception):
                    agent.close()
            with contextlib.suppress(Exception):
                self.engine.close()

        latency_summary = {
            names[seat]: self._latency_summary(latencies[seat]) for seat in (0, 1)
        }
        result = MatchResult(
            match_id=match_id,
            status=status,
            outcome=outcome,
            seed=int(seed),
            winner=winner,
            crowns=crowns,
            tick=tick,
            decisions=decision_count,
            agents=names,
            latency_ms=latency_summary,
            invalid_actions=tuple(illegal_counts),
            fault=fault,
            output_dir=str(destination) if destination else None,
        )
        if destination is not None:
            self._write_json(destination / "result.json", result.to_dict())
        return result


class _NullWriter:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, traceback):
        return False


def _null_writer():
    return _NullWriter()
