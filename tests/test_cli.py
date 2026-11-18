from __future__ import annotations

from royalebench.cli import build_parser


def test_cli_exposes_expected_v1_commands():
    parser = build_parser()
    args = parser.parse_args(["config-check"])
    assert args.command == "config-check"

    args = parser.parse_args(["tournament", "--agents", "random-legal-v1,hog-cycle-rules-v1"])
    assert args.command == "tournament"
    assert args.profile == "fast-250ms-v1"
