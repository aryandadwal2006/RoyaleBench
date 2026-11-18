"""Adapter over the pinned CRForge two-seat vector environment."""

from __future__ import annotations

import difflib
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from royalebench.config import V1_CONTENT_SHA, V1Config
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


def _verify_upstream_checkout(install: str | Path, expected_commit: str) -> Path:
    """Find the source checkout that built the installed env and verify its exact commit."""
    install_path = Path(install).expanduser().resolve()
    candidates = (install_path, *install_path.parents)
    source_root = next(
        (
            candidate
            for candidate in candidates
            if (candidate / ".git").exists()
            and ((candidate / "gradlew").is_file() or (candidate / "gradlew.bat").is_file())
        ),
        None,
    )
    if source_root is None:
        raise CrforgeEngineError(
            f"could not locate the CRForge source checkout above install path {install_path}; "
            "v1 requires a verifiable pinned source checkout"
        )
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CrforgeEngineError(f"could not verify CRForge source commit: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"git exited with {completed.returncode}"
        raise CrforgeEngineError(f"could not verify CRForge source commit: {detail}")
    actual_commit = completed.stdout.strip()
    if actual_commit != expected_commit:
        raise CrforgeEngineError(
            f"CRForge source commit mismatch: v1 requires {expected_commit}, got {actual_commit}"
        )
    return source_root


@dataclass(frozen=True, slots=True)
class BattleStep:
    done: bool
    info: dict[str, int]
    fault: dict[str, Any] | None


def _validate_runtime_metadata(
    metadata: dict[str, Any],
    *,
    config: V1Config,
    decision_ticks: int,
    schema: Any,
    id_version: int | None,
) -> None:
    """Reject an installed CRForge build whose runtime rules differ from the v1 contract."""
    expected_config = {
        "decision_ticks": int(decision_ticks),
        "level": config.card_level,
        "tower_level": config.tower_level,
        "max_ticks": config.max_ticks,
    }
    actual_config = metadata.get("config")
    if not isinstance(actual_config, dict):
        raise CrforgeEngineError("CRForge metadata does not expose its effective Ladder config")
    for key, expected in expected_config.items():
        actual = actual_config.get(key)
        if actual != expected:
            raise CrforgeEngineError(
                f"CRForge config mismatch for {key}: expected {expected}, got {actual!r}"
            )

    if metadata.get("mask_version") != config.mask_version:
        raise CrforgeEngineError(
            f"CRForge metadata mask_version is {metadata.get('mask_version')!r}; "
            f"v1 requires {config.mask_version}"
        )
    if id_version != 2:
        raise CrforgeEngineError(
            f"CRForge entity id_version is {id_version!r}; v1 requires seat-first-sight version 2"
        )
    if int(schema.play_delay_ticks) != 20:
        raise CrforgeEngineError(
            f"CRForge native PlayerCommands delay is {schema.play_delay_ticks} ticks; "
            "v1 requires 20"
        )


def _validate_game_data_identity(
    actual_version: str | None,
    actual_content_sha: str | None,
    *,
    expected_version: str,
) -> None:
    """Require the exact upstream table version and content fingerprint for v1."""
    if expected_version != "16.635.8":
        raise CrforgeEngineError(
            f"v1 cannot target game-data version {expected_version}; it fixes 16.635.8"
        )
    if actual_version != expected_version:
        raise CrforgeEngineError(
            f"game-data version mismatch: expected {expected_version}, got {actual_version}"
        )
    if actual_content_sha != V1_CONTENT_SHA:
        raise CrforgeEngineError(
            f"game-data content SHA mismatch: expected {V1_CONTENT_SHA}, got {actual_content_sha}"
        )


def _validate_initial_observations(
    observations: tuple[dict[str, Any], dict[str, Any]],
    *,
    deck_rows: tuple[str, ...],
    config: V1Config,
    decision_ticks: int,
) -> None:
    """Check the reset state agrees with the configured symmetric v1 match."""
    for seat, observation in enumerate(observations):
        if observation.get("seat") != seat:
            raise CrforgeEngineError(
                f"CRForge returned seat {observation.get('seat')!r} in observation slot {seat}"
            )
        if observation.get("game", {}).get("tick") != 0:
            raise CrforgeEngineError("CRForge reset did not begin at game tick 0")
        game = observation.get("game", {})
        if game.get("decision_ticks") != decision_ticks:
            raise CrforgeEngineError(
                f"seat {seat} reports decision_ticks={game.get('decision_ticks')!r}, "
                f"expected {decision_ticks}"
            )
        if game.get("play_delay_ticks") != 20:
            raise CrforgeEngineError(
                f"seat {seat} reports play_delay_ticks={game.get('play_delay_ticks')!r}, "
                "expected 20"
            )
        own = observation.get("own", {})
        if own.get("deck") != list(deck_rows):
            raise CrforgeEngineError(
                f"seat {seat} received a deck different from the frozen v1 deck: "
                f"{own.get('deck')!r}"
            )
        if own.get("deck_level") != [config.card_level] * 8:
            raise CrforgeEngineError(
                f"seat {seat} deck levels do not match configured level {config.card_level}: "
                f"{own.get('deck_level')!r}"
            )
        towers = own.get("towers", {})
        enemy_towers = observation.get("opponent", {}).get("towers", {})
        king_hp = towers.get("own_king", {}).get("max_hp")
        enemy_king_hp = enemy_towers.get("enemy_king", {}).get("max_hp")
        princess_hp = {
            towers.get("own_left", {}).get("max_hp"),
            towers.get("own_right", {}).get("max_hp"),
            enemy_towers.get("enemy_left", {}).get("max_hp"),
            enemy_towers.get("enemy_right", {}).get("max_hp"),
        }
        if king_hp is None or king_hp != enemy_king_hp:
            raise CrforgeEngineError(
                f"seat {seat} king tower levels are not mirrored: "
                f"own={king_hp}, enemy={enemy_king_hp}"
            )
        if None in princess_hp or len(princess_hp) != 1:
            raise CrforgeEngineError(
                f"seat {seat} princess tower max HP is not equal across both sides: {princess_hp}"
            )

    if observations[0]["own"]["deck"] != observations[1]["own"]["deck"]:
        raise CrforgeEngineError("the two seats did not receive the same mirrored v1 deck")
    for seat, observation in enumerate(observations):
        own_elixir = observation["own"]["elixir_scaled"]
        public_enemy_elixir = observation["opponent"]["estimated_elixir_scaled"]
        if own_elixir != public_enemy_elixir:
            raise CrforgeEngineError(
                f"seat {seat} initial public opponent elixir differs from starting elixir"
            )


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
        self.upstream_root = _verify_upstream_checkout(install, config.upstream_commit)
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
        self.decision_ticks = int(decision_ticks)
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
        try:
            _validate_runtime_metadata(
                self.vector.metadata,
                config=config,
                decision_ticks=self.decision_ticks,
                schema=self.schema,
                id_version=self.vector.id_version,
            )
        except CrforgeEngineError:
            self.close()
            raise
        except Exception as exc:
            self.close()
            raise CrforgeEngineError(f"could not validate CRForge runtime metadata: {exc}") from exc

        wanted_version = expected_data_version or config.data_version
        try:
            _validate_game_data_identity(
                self.vector.data_version,
                self.vector.content_sha,
                expected_version=wanted_version,
            )
        except CrforgeEngineError:
            self.close()
            raise

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
        observations = (self.observe(0), self.observe(1))
        _validate_initial_observations(
            observations,
            deck_rows=self.deck_rows,
            config=self.config,
            decision_ticks=self.decision_ticks,
        )
        return observations

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
