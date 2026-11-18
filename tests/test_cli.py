from __future__ import annotations

import sys

import pytest

from royalebench.agents.subprocess_agent import SubprocessAgent
from royalebench.cli import _agent_factories, build_parser


def test_cli_exposes_expected_v1_commands():
    parser = build_parser()
    args = parser.parse_args(["config-check"])
    assert args.command == "config-check"

    args = parser.parse_args(["tournament", "--agents", "random-legal-v1,hog-cycle-rules-v1"])
    assert args.command == "tournament"
    assert args.profile == "fast-250ms-v1"


def test_cli_builds_external_jsonl_agent_factory(tmp_path):
    factories = _agent_factories(
        ["random-legal-v1", "research-agent"],
        external_agent_name="research-agent",
        external_agent_command=[sys.executable, "worker.py"],
        external_agent_cwd=str(tmp_path),
        external_agent_env={"RESEARCH_AGENT_TOKEN": "participant-supplied"},
    )
    agent = factories["research-agent"]()
    try:
        assert isinstance(agent, SubprocessAgent)
        assert agent.name == "research-agent"
        assert agent.command == [sys.executable, "worker.py"]
        assert agent.cwd == str(tmp_path.resolve())
        assert agent.environment == {"RESEARCH_AGENT_TOKEN": "participant-supplied"}
    finally:
        agent.close()


def test_cli_requires_external_name_and_command_together():
    with pytest.raises(ValueError, match="must be supplied together"):
        _agent_factories(
            ["random-legal-v1", "research-agent"],
            external_agent_name="research-agent",
        )


def test_cli_requires_external_name_to_appear_in_agents():
    with pytest.raises(ValueError, match="must also appear"):
        _agent_factories(
            ["random-legal-v1", "hog-cycle-rules-v1"],
            external_agent_name="research-agent",
            external_agent_command=[sys.executable, "worker.py"],
        )


def test_tournament_cli_parses_external_command_as_json_array():
    args = build_parser().parse_args(
        [
            "tournament",
            "--agents",
            "random-legal-v1,research-agent",
            "--external-agent-name",
            "research-agent",
            "--external-agent-command",
            '["python", "worker.py"]',
            "--external-agent-pass-env",
            "MODEL_API_KEY,OTHER_TOKEN",
        ]
    )
    assert args.external_agent_command == ["python", "worker.py"]
    assert args.external_agent_name == "research-agent"
    assert args.external_agent_pass_env == "MODEL_API_KEY,OTHER_TOKEN"


def test_tournament_cli_rejects_non_array_external_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "tournament",
                "--external-agent-name",
                "research-agent",
                "--external-agent-command",
                '"python worker.py"',
            ]
        )

def test_tournament_rejects_duplicate_agent_identifiers():
    with pytest.raises(ValueError, match="must be unique"):
        _agent_factories(["llm", "llm"])


def test_forecast_eval_cli_parses_held_out_shard_and_horizons(tmp_path):
    args = build_parser().parse_args(
        [
            "forecast-eval",
            "--split",
            str(tmp_path / "test.jsonl.gz"),
            "--horizons",
            "1,2,4",
            "--output",
            str(tmp_path / "forecast.json"),
        ]
    )
    assert args.command == "forecast-eval"
    assert args.horizons == "1,2,4"
    assert args.output.endswith("forecast.json")
