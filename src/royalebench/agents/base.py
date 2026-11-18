"""Public agent contract for structured-state RoyaleBench matches."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Agent(Protocol):
    """The minimum lifecycle required of every in-process v1 agent."""

    name: str

    def reset(self, match_info: dict[str, Any]) -> None:
        """Start a fresh, isolated episode."""
        ...

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Return one ActionV1 JSON object for this observation."""
        ...

    def close(self) -> None:
        """Release resources allocated by this episode."""
        ...


class MatchInfo(dict[str, Any]):
    """Typed-by-convention metadata delivered at agent reset."""
