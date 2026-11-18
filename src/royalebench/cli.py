"""Command-line interface for configuring and running RoyaleBench v1."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from royalebench.agents.baselines import HogCycleAgent, NoOpAgent, RandomLegalAgent
from royalebench.config import load_config
from royalebench.dataset import build_dataset
from royalebench.engine.crforge import CrforgeBattle
from royalebench.runner import MatchRunner
from royalebench.tournament import TournamentRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _engine_paths(config: Any) -> tuple[Path, Path]:
    root = _root()
    install = Path(
        os.environ.get(
            "ROYALEBENCH_CRFORGE_INSTALL",
            str(root / "third_party" / "upstream" / "crforge" / "env" / "build" / "install" / "env"),
        )
    )
    tables = Path(
        os.environ.get(
            "ROYALEBENCH_CRFORGE_TABLES",
            str(Path.home() / ".crforge" / "tables" / config.data_version),
        )
    )
    return install, tables


def _engine_factory(config: Any):
    install, tables = _engine_paths(config)

    def create(decision_ticks: int) -> CrforgeBattle:
        return CrforgeBattle(
            config,
            install=install,
            tables=tables,
            decision_ticks=decision_ticks,
            expected_data_version=config.data_version,
        )

    return create


def _agent_factories(names: list[str]) -> dict[str, Any]:
    factories: dict[str, Any] = {
        "noop-v1": NoOpAgent,
        "random-legal-v1": RandomLegalAgent,
        "hog-cycle-rules-v1": HogCycleAgent,
    }
    selected: dict[str, Any] = {}
    for name in names:
        if name == "llm":
            from royalebench.agents.openai_compatible import OpenAICompatibleAgent

            agent = OpenAICompatibleAgent()
            selected[agent.name] = lambda model=agent.model: OpenAICompatibleAgent(model=model)
            agent.close()
            continue
        if name not in factories:
            raise ValueError(
                f"unknown agent {name!r}; available: {', '.join(sorted(factories))}, llm"
            )
        selected[name] = factories[name]
    if len(selected) < 2:
        raise ValueError("choose at least two distinct agents")
    return selected


def _load(args: argparse.Namespace):
    path = Path(args.config) if args.config else _root() / "configs" / "v1.yaml"
    return load_config(path)


def _cmd_config_check(args: argparse.Namespace) -> int:
    config = _load(args)
    print(json.dumps({
        "valid": True,
        "deck": list(config.deck),
        "data_version": config.data_version,
        "card_level": config.card_level,
        "tower_level": config.tower_level,
        "profiles": dict(config.decision_profiles),
        "mask_version": config.mask_version,
        "action_resolution": config.action_resolution,
    }, indent=2))
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    config = _load(args)
    ticks = config.ticks_for_profile(args.profile)
    engine = _engine_factory(config)(ticks)
    runner = MatchRunner(
        engine,
        profile=args.profile,
        profile_ticks=ticks,
        request_timeout_s=args.timeout,
    )
    result = runner.run(
        (RandomLegalAgent(wait_probability=0.1), HogCycleAgent()),
        seed=args.seed,
        match_id=args.match_id,
        output_dir=args.output,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.status == "completed" else 2


def _cmd_tournament(args: argparse.Namespace) -> int:
    config = _load(args)
    ticks = config.ticks_for_profile(args.profile)
    factories = _agent_factories(args.agents.split(","))
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    tournament = TournamentRunner(
        _engine_factory(config),
        profile=args.profile,
        profile_ticks=ticks,
        request_timeout_s=args.timeout,
    )
    summary = tournament.run_round_robin(factories, seeds, output_dir=args.output)
    print(json.dumps(summary, indent=2))
    return 0 if summary["completed_matches"] == summary["total_matches"] else 2


def _cmd_dataset(args: argparse.Namespace) -> int:
    manifest = build_dataset(
        args.matches,
        args.output,
        split_seed=args.split_seed,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
    )
    print(json.dumps(manifest, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="royalebench")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument(
            "--config", default=None, help="YAML config (default: configs/v1.yaml)"
        )

    config_parser = sub.add_parser("config-check", help="validate and print v1 configuration")
    common(config_parser)
    config_parser.set_defaults(handler=_cmd_config_check)

    smoke = sub.add_parser("smoke", help="run one headless random-vs-rule-based battle")
    common(smoke)
    smoke.add_argument("--profile", default="fast-250ms-v1")
    smoke.add_argument("--seed", type=int, default=42)
    smoke.add_argument("--match-id", default="royalebench-smoke")
    smoke.add_argument("--timeout", type=float, default=120.0)
    smoke.add_argument("--output", default="results/smoke/match")
    smoke.set_defaults(handler=_cmd_smoke)

    tournament = sub.add_parser("tournament", help="run a paired round-robin tournament")
    common(tournament)
    tournament.add_argument("--profile", default="fast-250ms-v1")
    tournament.add_argument("--agents", default="random-legal-v1,hog-cycle-rules-v1")
    tournament.add_argument("--seeds", default="11,22")
    tournament.add_argument("--timeout", type=float, default=120.0)
    tournament.add_argument("--output", default="results/tournament")
    tournament.set_defaults(handler=_cmd_tournament)

    dataset = sub.add_parser("dataset", help="export match-level trajectory train/val/test splits")
    dataset.add_argument("--matches", required=True, help="directory containing match result folders")
    dataset.add_argument("--output", default="results/dataset")
    dataset.add_argument("--split-seed", type=int, default=20261118)
    dataset.add_argument("--validation-fraction", type=float, default=0.1)
    dataset.add_argument("--test-fraction", type=float, default=0.1)
    dataset.set_defaults(handler=_cmd_dataset)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ValueError, FileNotFoundError, RuntimeError, KeyError) as exc:
        print(f"royalebench: error: {exc}", file=sys.stderr)
        return 2
