"""Versioned configuration for the first RoyaleBench release."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

V1_CRFORGE_COMMIT = "fa5959055c590a493d62c8dbc804e602832d08a6"
V1_DATA_VERSION = "16.635.8"
V1_CONTENT_SHA = "062a11e0500c03cc041f123413b1ef1846b539a4"
V1_CARD_LEVEL = 11
V1_TOWER_LEVEL = 11
V1_MAX_TICKS = 9000

V1_DECK = (
    "Cannon",
    "Fireball",
    "HogRider",
    "IceGolem",
    "IceSpirit",
    "Musketeer",
    "Skeletons",
    "TheLog",
)
V1_PROFILES = (("fast-250ms-v1", 5), ("llm-api-1s-v1", 20))


@dataclass(frozen=True, slots=True)
class V1Config:
    """The frozen game rules shared by every structured-state v1 match."""

    deck: tuple[str, ...] = V1_DECK
    upstream_commit: str = V1_CRFORGE_COMMIT
    data_version: str = V1_DATA_VERSION
    card_level: int = V1_CARD_LEVEL
    tower_level: int = V1_TOWER_LEVEL
    max_ticks: int = V1_MAX_TICKS
    mask_version: int = 1
    action_resolution: str = "tile-center-v1"
    decision_profiles: tuple[tuple[str, int], ...] = V1_PROFILES

    def __post_init__(self) -> None:
        if len(self.deck) != 8:
            raise ValueError(f"v1 requires exactly eight deck cards, got {len(self.deck)}")
        if any(not isinstance(card, str) or not card.strip() for card in self.deck):
            raise ValueError("deck card names must be non-empty strings")
        if len(set(self.deck)) != 8:
            raise ValueError("the v1 deck must contain eight distinct cards")
        if tuple(self.deck) != V1_DECK:
            raise ValueError("v1 fixes the exact mirrored Hog 2.6 deck and card ordering")
        if self.upstream_commit != V1_CRFORGE_COMMIT:
            raise ValueError("v1 fixes the pinned CRForge source commit")
        if self.data_version != V1_DATA_VERSION:
            raise ValueError("v1 fixes CRForge game-data version 16.635.8")
        if self.card_level != V1_CARD_LEVEL or self.tower_level != V1_TOWER_LEVEL:
            raise ValueError("v1 fixes card and tower levels at 11")
        if self.max_ticks != V1_MAX_TICKS:
            raise ValueError("v1 fixes the engine tick limit at 9000")
        if self.decision_profiles != V1_PROFILES:
            raise ValueError("v1 fixes the fast-250ms-v1 and llm-api-1s-v1 decision profiles")
        if self.mask_version != 1:
            raise ValueError("v1 fixes CRForge MASK_ALL_TILES semantics (mask_version=1)")
        if self.action_resolution != "tile-center-v1":
            raise ValueError("v1 fixes the 18x32 tile-centre action grid")
        names = [name for name, _ in self.decision_profiles]
        if len(set(names)) != len(names) or not names:
            raise ValueError("decision profile names must be unique and non-empty")
        if any(ticks < 1 for _, ticks in self.decision_profiles):
            raise ValueError("decision profile tick counts must be positive")

    def ticks_for_profile(self, profile: str) -> int:
        for name, ticks in self.decision_profiles:
            if name == profile:
                return ticks
        choices = ", ".join(name for name, _ in self.decision_profiles)
        raise KeyError(f"unknown decision profile {profile!r}; available: {choices}")

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> V1Config:
        match = raw.get("match", {})
        profiles = raw.get("decision_profiles", {})
        engine = raw.get("engine", {})
        if not all(isinstance(value, dict) for value in (match, profiles, engine)):
            raise ValueError(
                "configuration sections 'engine', 'match' and 'decision_profiles' must be mappings"
            )
        deck_raw = match.get("deck", list(V1_DECK))
        if not isinstance(deck_raw, list):
            raise ValueError("match.deck must be a list")
        profile_rows = tuple((str(name), int(ticks)) for name, ticks in profiles.items())
        return cls(
            deck=tuple(str(card) for card in deck_raw),
            upstream_commit=str(engine.get("upstream_commit", V1_CRFORGE_COMMIT)),
            data_version=str(engine.get("data_version", V1_DATA_VERSION)),
            card_level=int(match.get("card_level", V1_CARD_LEVEL)),
            tower_level=int(match.get("tower_level", V1_TOWER_LEVEL)),
            max_ticks=int(match.get("max_ticks", V1_MAX_TICKS)),
            mask_version=int(match.get("mask_version", 1)),
            action_resolution=str(match.get("action_resolution", "tile-center-v1")),
            decision_profiles=profile_rows or V1_PROFILES,
        )


def load_config(path: str | Path) -> V1Config:
    """Load the small YAML release configuration."""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "YAML config loading requires PyYAML; install RoyaleBench dependencies"
        ) from exc

    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{source} must contain a YAML mapping")
    return V1Config.from_mapping(raw)
