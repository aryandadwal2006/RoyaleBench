from __future__ import annotations

import pytest

from royalebench.config import (
    V1_CONTENT_SHA,
    V1_CRFORGE_COMMIT,
    V1_DATA_VERSION,
    V1_DECK,
    V1_PROFILES,
    V1Config,
    load_config,
)


def test_v1_config_freezes_hog_cycle_deck_and_profiles() -> None:
    config = V1Config()
    assert config.deck == V1_DECK
    assert len(config.deck) == 8
    assert len(set(config.deck)) == 8
    assert config.upstream_commit == V1_CRFORGE_COMMIT
    assert config.data_version == V1_DATA_VERSION
    assert config.decision_profiles == V1_PROFILES
    assert V1_CONTENT_SHA == "062a11e0500c03cc041f123413b1ef1846b539a4"
    assert config.ticks_for_profile("fast-250ms-v1") == 5
    assert config.ticks_for_profile("llm-api-1s-v1") == 20
    assert config.mask_version == 1
    assert config.action_resolution == "tile-center-v1"


def test_v1_config_rejects_duplicate_cards() -> None:
    with pytest.raises(ValueError, match="distinct"):
        V1Config(deck=("Cannon",) * 8)


def test_v1_config_rejects_noncanonical_deck() -> None:
    with pytest.raises(ValueError, match="exact mirrored Hog 2.6 deck"):
        V1Config(deck=("Knight",) + V1_DECK[1:])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"upstream_commit": "0" * 40}, "pinned CRForge source commit"),
        ({"data_version": "16.635.3"}, "game-data version"),
        ({"card_level": 10}, "levels at 11"),
        ({"tower_level": 10}, "levels at 11"),
        ({"max_ticks": 8000}, "tick limit at 9000"),
        ({"decision_profiles": (("fast-250ms-v1", 10),)}, "decision profiles"),
    ],
)
def test_v1_config_rejects_canonical_match_drift(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        V1Config(**kwargs)


def test_v1_config_rejects_other_mask_semantics() -> None:
    with pytest.raises(ValueError, match="MASK_ALL_TILES"):
        V1Config(mask_version=2)


def test_unknown_profile_is_explicit() -> None:
    with pytest.raises(KeyError, match="unknown decision profile"):
        V1Config().ticks_for_profile("not-a-profile")


def test_yaml_config_loads_release_settings(tmp_path) -> None:
    source = tmp_path / "v1.yaml"
    source.write_text(
        f"engine:\n  upstream_commit: '{V1_CRFORGE_COMMIT}'\n"
        f"  data_version: '{V1_DATA_VERSION}'\n"
        "match:\n  card_level: 11\n  tower_level: 11\n"
        "decision_profiles:\n  fast-250ms-v1: 5\n  llm-api-1s-v1: 20\n",
        encoding="utf-8",
    )
    config = load_config(source)
    assert config.upstream_commit == V1_CRFORGE_COMMIT
    assert config.data_version == V1_DATA_VERSION
    assert config.card_level == 11
    assert config.tower_level == 11
    assert config.ticks_for_profile("fast-250ms-v1") == 5
    assert config.ticks_for_profile("llm-api-1s-v1") == 20
