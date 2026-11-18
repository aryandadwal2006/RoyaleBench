"""OpenAI Chat Completions-compatible structured-action agent."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

_SYSTEM_PROMPT = """You are an agent competing in the RoyaleBench v1 offline Clash Royale simulator.
Return exactly one JSON object matching ActionV1.
Do not return markdown, explanations, or extra fields.

Rules:
- Use only the supplied observation. It contains player-visible state, not hidden simulator state.
- A play uses a current hand_slot and the exact expected_card string in that slot.
- x_tile and y_tile are tile-centre coordinates: x is 0.5, 1.5, ..., 17.5; y is
  0.5, 1.5, ..., 31.5. Coordinates are in your own seat's frame, with your king at the bottom.
- Select only a card whose slot appears in legal_actions.playable_slots.
- Use an ability only when its slot appears in legal_actions.ability_slots.
- Wait is always valid. Never invent cards, fields, elixir, enemies, or future information.
- The environment applies native placement search and the game's command delay after your action.
"""


class OpenAICompatibleAgent:
    """One synchronous Chat Completions request per decision.

    Configure model, endpoint and key explicitly or through ROYALEBENCH_LLM_* environment
    variables. No specific model identifier is assumed.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 60.0,
        temperature: float = 0.0,
        max_tokens: int = 300,
    ) -> None:
        self.model = model or os.environ.get("ROYALEBENCH_LLM_MODEL", "")
        self.base_url = (
            base_url or os.environ.get("ROYALEBENCH_LLM_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("ROYALEBENCH_LLM_API_KEY", "")
        if not self.model.strip():
            raise ValueError("set ROYALEBENCH_LLM_MODEL or pass model= explicitly")
        if not self.api_key.strip():
            raise ValueError("set ROYALEBENCH_LLM_API_KEY or pass api_key= explicitly")
        if timeout_s <= 0 or max_tokens < 1:
            raise ValueError("timeout_s and max_tokens must be positive")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be in [0, 2]")
        self.timeout_s = float(timeout_s)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.model).strip("-")
        self.name = f"llm-{slug or 'configured-model'}"
        self.last_telemetry: dict[str, Any] | None = None
        self.match_info: dict[str, Any] = {}

    def reset(self, match_info: dict[str, Any]) -> None:
        self.match_info = {
            "match_id": match_info.get("match_id"),
            "seed": match_info.get("seed"),
            "seat": match_info.get("seat"),
            "profile": match_info.get("profile"),
        }

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read(4096).decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM endpoint returned HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM endpoint request failed: {exc.reason}") from exc
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0

        try:
            content = result["choices"][0]["message"]["content"]
            action = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("LLM endpoint did not return a JSON ActionV1 object") from exc
        if not isinstance(action, dict):
            raise RuntimeError("LLM action output must be a JSON object")

        usage = result.get("usage")
        self.last_telemetry = {
            "provider": "openai-compatible",
            "model": self.model,
            "latency_ms_client": elapsed_ms,
            "usage": usage if isinstance(usage, dict) else None,
        }
        return action

    def close(self) -> None:
        self.match_info = {}
