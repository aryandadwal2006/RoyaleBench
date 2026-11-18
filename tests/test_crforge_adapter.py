from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from royalebench.config import V1_CONTENT_SHA, V1Config
from royalebench.engine.crforge import (
    CrforgeEngineError,
    _validate_game_data_identity,
    _validate_initial_observations,
    _validate_runtime_metadata,
    _verify_upstream_checkout,
)


def _metadata(**overrides):
    config = {
        "decision_ticks": 5,
        "level": 11,
        "tower_level": 11,
        "max_ticks": 9000,
    }
    config.update(overrides.pop("config", {}))
    return {"config": config, "mask_version": overrides.pop("mask_version", 1)}


def _observations():
    deck = list(V1Config().deck)
    seats = []
    for seat in (0, 1):
        seats.append(
            {
                "seat": seat,
                "game": {"tick": 0, "decision_ticks": 5, "play_delay_ticks": 20},
                "own": {
                    "deck": list(deck),
                    "deck_level": [11] * 8,
                    "elixir_scaled": 50000,
                    "towers": {
                        "own_king": {"max_hp": 5000},
                        "own_left": {"max_hp": 3000},
                        "own_right": {"max_hp": 3000},
                    },
                },
                "opponent": {
                    "estimated_elixir_scaled": 50000,
                    "towers": {
                        "enemy_king": {"max_hp": 5000},
                        "enemy_left": {"max_hp": 3000},
                        "enemy_right": {"max_hp": 3000},
                    },
                },
            }
        )
    return tuple(seats)


def test_runtime_metadata_accepts_the_frozen_crforge_contract():
    _validate_runtime_metadata(
        _metadata(),
        config=V1Config(),
        decision_ticks=5,
        schema=SimpleNamespace(play_delay_ticks=20),
        id_version=2,
    )


@pytest.mark.parametrize(
    ("metadata", "decision_ticks", "delay", "id_version", "message"),
    [
        (_metadata(config={"level": 10}), 5, 20, 2, "config mismatch for level"),
        (_metadata(config={"tower_level": 10}), 5, 20, 2, "config mismatch for tower_level"),
        (_metadata(config={"decision_ticks": 20}), 5, 20, 2, "config mismatch for decision_ticks"),
        (_metadata(config={"max_ticks": 8000}), 5, 20, 2, "config mismatch for max_ticks"),
        (_metadata(mask_version=2), 5, 20, 2, "mask_version"),
        (_metadata(), 5, 19, 2, "delay is 19"),
        (_metadata(), 5, 20, 1, "id_version is 1"),
    ],
)
def test_runtime_metadata_rejects_semantic_drift(
    metadata, decision_ticks, delay, id_version, message
):
    with pytest.raises(CrforgeEngineError, match=message):
        _validate_runtime_metadata(
            metadata,
            config=V1Config(),
            decision_ticks=decision_ticks,
            schema=SimpleNamespace(play_delay_ticks=delay),
            id_version=id_version,
        )


def test_runtime_metadata_requires_effective_config():
    with pytest.raises(CrforgeEngineError, match="does not expose"):
        _validate_runtime_metadata(
            {"mask_version": 1},
            config=V1Config(),
            decision_ticks=5,
            schema=SimpleNamespace(play_delay_ticks=20),
            id_version=2,
        )


def test_game_data_identity_accepts_exact_locked_version_and_content():
    _validate_game_data_identity(
        "16.635.8",
        V1_CONTENT_SHA,
        expected_version="16.635.8",
    )


@pytest.mark.parametrize(
    ("version", "content_sha", "expected_version", "message"),
    [
        ("16.635.3", V1_CONTENT_SHA, "16.635.8", "version mismatch"),
        ("16.635.8", "0" * 40, "16.635.8", "content SHA mismatch"),
        ("16.635.8", V1_CONTENT_SHA, "16.635.3", "v1 cannot target"),
    ],
)
def test_game_data_identity_rejects_version_or_content_drift(
    version, content_sha, expected_version, message
):
    with pytest.raises(CrforgeEngineError, match=message):
        _validate_game_data_identity(
            version,
            content_sha,
            expected_version=expected_version,
        )


def test_initial_observations_accept_equal_mirrored_match():
    _validate_initial_observations(
        _observations(),
        deck_rows=tuple(V1Config().deck),
        config=V1Config(),
        decision_ticks=5,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda obs: obs[0].update(seat=1), "observation slot 0"),
        (lambda obs: obs[0]["game"].update(tick=5), "tick 0"),
        (lambda obs: obs[1]["own"].update(deck_level=[10] * 8), "deck levels"),
        (lambda obs: obs[0]["own"].update(deck=obs[0]["own"]["deck"][:-1]), "frozen v1 deck"),
        (lambda obs: obs[0]["game"].update(decision_ticks=20), "decision_ticks"),
        (lambda obs: obs[1]["game"].update(play_delay_ticks=10), "play_delay_ticks"),
        (
            lambda obs: obs[0]["own"]["towers"]["own_king"].update(max_hp=4999),
            "king tower",
        ),
        (
            lambda obs: obs[0]["opponent"]["towers"]["enemy_right"].update(max_hp=2500),
            "princess tower max HP",
        ),
        (
            lambda obs: obs[1]["opponent"].update(estimated_elixir_scaled=40000),
            "initial public opponent elixir",
        ),
    ],
)
def test_initial_observations_reject_mismatched_v1_setup(mutation, message):
    observations = deepcopy(_observations())
    mutation(observations)
    with pytest.raises(CrforgeEngineError, match=message):
        _validate_initial_observations(
            tuple(observations),
            deck_rows=tuple(V1Config().deck),
            config=V1Config(),
            decision_ticks=5,
        )


def test_initial_observations_reject_seat_deck_disagreement():
    observations = [dict(row) for row in _observations()]
    observations[1] = deepcopy(observations[1])
    observations[1]["own"]["deck"] = list(reversed(V1Config().deck))

    with pytest.raises(CrforgeEngineError, match="same mirrored v1 deck"):
        _validate_initial_observations(
            tuple(observations),
            deck_rows=tuple(V1Config().deck),
            config=V1Config(),
            decision_ticks=5,
        )


def test_upstream_checkout_verifies_the_exact_pinned_commit(tmp_path, monkeypatch):
    source = tmp_path / "crforge"
    install = source / "env" / "build" / "install" / "env"
    install.mkdir(parents=True)
    (source / ".git").write_text("gitdir: ../.git/modules/crforge\n", encoding="utf-8")
    (source / "gradlew.bat").write_text("@echo off\n", encoding="utf-8")
    completed = SimpleNamespace(
        returncode=0,
        stdout=V1Config().upstream_commit + "\n",
        stderr="",
    )
    monkeypatch.setattr(
        "royalebench.engine.crforge.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    assert _verify_upstream_checkout(install, V1Config().upstream_commit) == source.resolve()


def test_upstream_checkout_rejects_a_different_commit(tmp_path, monkeypatch):
    source = tmp_path / "crforge"
    install = source / "env" / "build" / "install" / "env"
    install.mkdir(parents=True)
    (source / ".git").write_text("gitdir: ../.git/modules/crforge\n", encoding="utf-8")
    (source / "gradlew.bat").write_text("@echo off\n", encoding="utf-8")
    completed = SimpleNamespace(returncode=0, stdout="0" * 40 + "\n", stderr="")
    monkeypatch.setattr(
        "royalebench.engine.crforge.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(CrforgeEngineError, match="source commit mismatch"):
        _verify_upstream_checkout(install, V1Config().upstream_commit)


def test_upstream_checkout_requires_a_verifiable_source_tree(tmp_path):
    install = tmp_path / "untracked-install" / "env"
    install.mkdir(parents=True)

    with pytest.raises(CrforgeEngineError, match="could not locate"):
        _verify_upstream_checkout(install, V1Config().upstream_commit)
