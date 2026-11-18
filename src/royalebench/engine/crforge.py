"""Adapter over the pinned CRForge two-seat vector environment."""

from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from royalebench.config import V1Config
from royalebench.engine.actions import to_crforge_action
from royalebench.observations import build_observation

_CARD_ALIASES = {
    "thelog": ("thelog", "log"),
    "log": ("log", "thelog"),
    "icespirit": ("icespirit", "icespirits"),
}


def _normalize_card_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _resolve_deck_rows(deck: Sequence[str], vocabulary: Sequence[str]) -> tuple[str, ...]:
    """Resolve UI/deck-list names to this pinned data table's exact row names."""
    normalized: dict[str, str] = {}
    for row in vocabulary:
        normalized.setdefault(_normalize_card_name(row), row)

    resolved: list[str] = []
    for requested in deck:
        key = _normalize_card_name(requested)
        aliases = _CARD_ALIASES.get(key, (key,))
        match = next((normalized[alias] for alias in aliases if alias in normalized), None)
        if match is None:
            suggestions = difflib.get_close_matches(requested, list(vocabulary), n=5, cutoff=0.4)
            raise ValueError(
                f"deck card {requested!r} is not in this CRForge vocabulary; "
                f"nearby row names: {suggestions}"
            )
        resolved.append(match)

    if len(set(resolved)) != len(resolved):
        raise ValueError("two configured deck labels resolve to the same CRForge card row")
    return tuple(resolved)


class CrforgeEngineError(RuntimeError):
    """CRForge could not start or complete a benchmark battle."""


@dataclass(frozen=True, slots=True)
class BattleStep:
    done: bool
    info: dict[str, int]
    fault: dict[str, Any] | None


class CrforgeBattle:
    """One synchronized two-seat battle driven by the CRForge JVM environment."""

    def __init__(
        self,
        config: V1Config,
        *,
        install: str | Path,
        tables: str | Path,
        decision_ticks: int = 5,
        expected_data_version: str | None = None,
    ) -> None:
        try:
            from crforge_env import LadderConfig, VectorBattle
        except ImportError as exc:
            raise CrforgeEngineError(
                "crforge-env is not installed. Run scripts/build_engine.ps1 to build the CRForge "
                "env distribution and install its Python package."
            ) from exc

        ladder_config = LadderConfig(
            decision_ticks=decision_ticks,
            level=config.card_level,
            tower_level=config.tower_level,
            max_ticks=config.max_ticks,
            mask_version=config.mask_version,
        )
        try:
            self.vector = VectorBattle(
                1, 1, install=install, engine="ladder", tables=tables, config=ladder_config
            )
        except Exception as exc:
            raise CrforgeEngineError(f"could not initialize CRForge: {exc}") from exc

        self.config = config
        self.schema = self.vector.schema
        self.vector.set_autoreset(False)
        if (self.schema.cols, self.schema.rows) != (18, 32):
            self.close()
            raise CrforgeEngineError(
                f"unsupported CRForge action grid {self.schema.cols}x{self.schema.rows}; "
                "v1 requires 18x32"
            )
        if self.vector.mask_version != 1:
            self.close()
            raise CrforgeEngineError(
                f"CRForge mask version is {self.vector.mask_version}; "
                "v1 requires MASK_ALL_TILES=1"
            )
        wanted_version = expected_data_version or config.data_version
        if self.vector.data_version != wanted_version:
            actual = self.vector.data_version
            self.close()
            raise CrforgeEngineError(
                f"game-data version mismatch: expected {wanted_version}, got {actual}"
            )

        try:
            self.deck_rows = _resolve_deck_rows(config.deck, self.vector.vocabulary)
        except ValueError as exc:
            self.close()
            raise CrforgeEngineError(str(exc)) from exc

        self._match_id: str | None = None
        self._decision_id = 0

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self.vector.metadata)

    def reset(self, seed: int, *, match_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if not -(2**31) <= int(seed) < 2**31:
            raise ValueError("CRForge match seeds must be signed 32-bit integers")
        self._match_id = match_id
        self._decision_id = 0
        try:
            self.vector.reset([int(seed)], self.deck_rows, self.deck_rows)
        except Exception as exc:
            raise CrforgeEngineError(
                f"CRForge refused the fixed v1 deck or match setup: {exc}"
            ) from exc
        if bool(self.vector.dones[0]):
            fault = self.vector.fault(0)
            raise CrforgeEngineError(f"CRForge faulted during reset: {fault}")
        return self.observe(0), self.observe(1)

    def observe(self, seat: int) -> dict[str, Any]:
        if seat not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        if self._match_id is None:
            raise RuntimeError("reset the battle before requesting observations")
        raw = self.vector.observations[0, seat].copy()
        mask = self.vector.masks[0, seat].copy()
        return build_observation(
            self.vector,
            raw,
            mask,
            match_id=self._match_id,
            decision_id=self._decision_id,
            seat=seat,
        )

    def encode_action(self, seat: int, raw_action: object) -> tuple[int, bool]:
        if seat not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        raw = self.vector.observations[0, seat].copy()
        mask = self.vector.masks[0, seat].copy()
        return to_crforge_action(
            raw_action,
            schema=self.schema,
            raw_observation=raw,
            action_mask=mask,
            card_name_lookup=lambda card_id: (
                self.vector.vocabulary[card_id]
                if 0 <= int(card_id) < len(self.vector.vocabulary)
                else None
            ),
        )

    def step(self, actions: Sequence[int]) -> BattleStep:
        if len(actions) != 2:
            raise ValueError("a CRForge battle needs exactly two seat actions")
        self.vector.step(np.asarray([actions], dtype=np.int32))
        info = self.vector.info(0)
        fault_obj = self.vector.fault(0)
        fault = None
        if fault_obj is not None:
            fault = {
                "kind": fault_obj.kind,
                "exception": fault_obj.exception,
                "message": fault_obj.message,
                "signature": fault_obj.signature,
                "tick": fault_obj.tick,
                "bundle": fault_obj.bundle,
            }
        self._decision_id += 1
        return BattleStep(done=bool(self.vector.dones[0]), info=info, fault=fault)

    def close(self) -> None:
        vector = getattr(self, "vector", None)
        if vector is not None:
            vector.close()
