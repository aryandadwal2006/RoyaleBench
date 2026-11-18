from __future__ import annotations

import pytest

from royalebench.config import V1Config, load_config


def test_v1_config_freezes_hog_cycle_deck_and_profiles() -> None:
    config = V1Config()
    assert len(config.deck) == 8
    assert len(set(config.deck)) == 8
    assert config.ticks_for_profile("fast-250ms-v1") == 5
    assert config.ticks_for_profile("llm-api-1s-v1") == 20
    assert config.mask_version == 1
    assert config.action_resolution == "tile-center-v1"


def test_v1_config_rejects_duplicate_cards() -> None:
    with pytest.raises(ValueError, match="distinct"):
        V1Config(deck=("Cannon",) * 8)


def test_v1_config_rejects_other_mask_semantics() -> None:
    with pytest.raises(ValueError, match="MASK_ALL_TILES"):
        V1Config(mask_version=2)


def test_unknown_profile_is_explicit() -> None:
    with pytest.raises(KeyError, match="unknown decision profile"):
        V1Config().ticks_for_profile("not-a-profile")


def test_yaml_config_loads_release_settings(tmp_path) -> None:
    source = tmp_path / "v1.yaml"
    source.write_text(
        "engine:\n  data_version: '16.635.8'\n"
        "match:\n  card_level: 11\n  tower_level: 11\n"
        "decision_profiles:\n  fast-250ms-v1: 5\n",
        encoding="utf-8",
    )
    config = load_config(source)
    assert config.data_version == "16.635.8"
    assert config.card_level == 11
    assert config.ticks_for_profile("fast-250ms-v1") == 5
