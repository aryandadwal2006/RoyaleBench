"""Persistent JSONL subprocess adapter for untrusted third-party agents."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

from royalebench.observations import observation_hash
from royalebench.protocol.actions import ActionResolution
from royalebench.protocol.responses import AgentResponse


_AGENT_EVENT_SCHEMA = "royalebench.agent-event.v1"
_AGENT_REQUEST_SCHEMA = "royalebench.agent-request.v1"


class SubprocessAgent:
    """A persistent child process speaking the RoyaleBench JSONL agent protocol.

    The child receives only reset metadata and seat-visible observations. Standard output is
    reserved for protocol JSONL. Standard error is inherited for diagnostics. The child is killed
    when a request exceeds its configured timeout.
    """

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_s: float = 120.0,
        startup_timeout_s: float = 30.0,
        shutdown_timeout_s: float = 3.0,
    ) -> None:
        if not name.strip():
            raise ValueError("agent name must be non-empty")
        if not command or any(not str(part) for part in command):
            raise ValueError("subprocess command must be a non-empty argument sequence")
        if timeout_s <= 0 or startup_timeout_s <= 0 or shutdown_timeout_s <= 0:
            raise ValueError("all subprocess timeouts must be positive")
        self.name = name
        self.command = [str(part) for part in command]
        self.cwd = str(Path(cwd).resolve()) if cwd is not None else None
        self.environment = {str(key): str(value) for key, value in (env or {}).items()}
        self.timeout_s = float(timeout_s)
        self.startup_timeout_s = float(startup_timeout_s)
        self.shutdown_timeout_s = float(shutdown_timeout_s)
        self.last_telemetry: dict[str, Any] | None = None
        self._process: subprocess.Popen[str] | None = None
        self._messages: queue.Queue[str | None | BaseException] | None = None
        self._match_info: dict[str, Any] = {}
        self._reader: threading.Thread | None = None

    def set_timeout(self, timeout_s: float) -> None:
        if timeout_s <= 0:
            raise ValueError("subprocess timeout must be positive")
        self.timeout_s = float(timeout_s)

    @staticmethod
    def _base_environment() -> dict[str, str]:
        # Avoid leaking provider keys or unrelated host secrets into submitted agent processes.
        allowed = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "VIRTUAL_ENV",
            "PYTHONPATH",
        }
        return {key: value for key, value in os.environ.items() if key.upper() in allowed}

    def _send(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            raise RuntimeError(f"agent subprocess {self.name!r} is not running")
        process.stdin.write(json.dumps(message, separators=(",", ":"), ensure_ascii=False))
        process.stdin.write("\n")
        process.stdin.flush()

    def _read_stdout(self) -> None:
        process = self._process
        messages = self._messages
        if process is None or process.stdout is None or messages is None:
            return
        try:
            for line in process.stdout:
                messages.put(line)
        except BaseException as exc:
            messages.put(exc)
        finally:
            messages.put(None)

    def _receive(self, timeout_s: float) -> dict[str, Any]:
        messages = self._messages
        if messages is None:
            raise RuntimeError("agent subprocess has not been started")
        try:
            item = messages.get(timeout=timeout_s)
        except queue.Empty as exc:
            self._terminate()
            raise TimeoutError(f"agent {self.name!r} exceeded {timeout_s:.3f}s response timeout") from exc
        if isinstance(item, BaseException):
            raise RuntimeError(f"failed reading agent {self.name!r} stdout: {item}") from item
        if item is None:
            process = self._process
            code = process.poll() if process is not None else None
            raise RuntimeError(f"agent subprocess {self.name!r} closed stdout (exit={code})")
        try:
            payload = json.loads(item)
        except json.JSONDecodeError as exc:
            raise ValueError(f"agent {self.name!r} wrote invalid JSONL: {item[:300]!r}") from exc
        if not isinstance(payload, dict):
            raise ValueError("agent protocol messages must be JSON objects")
        return payload

    def reset(self, match_info: dict[str, Any]) -> None:
        self.close()
        self._match_info = dict(match_info)
        child_env = self._base_environment()
        child_env.update(self.environment)
        self._messages = queue.Queue()
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=child_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as exc:
            self._process = None
            raise RuntimeError(f"could not launch agent {self.name!r}: {exc}") from exc

        self._reader = threading.Thread(
            target=self._read_stdout,
            name=f"royalebench-reader-{self.name}",
            daemon=True,
        )
        self._reader.start()
        self.last_telemetry = None
        try:
            self._send(
                {
                    "schema": _AGENT_EVENT_SCHEMA,
                    "type": "start",
                    "match_info": self._match_info,
                }
            )
            ready = self._receive(self.startup_timeout_s)
            if ready.get("schema") != _AGENT_EVENT_SCHEMA or ready.get("type") != "ready":
                raise ValueError("agent must acknowledge start with an agent-event.v1 ready message")
        except Exception:
            self._terminate()
            raise

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        if self._process is None:
            raise RuntimeError("call reset before asking a subprocess agent to act")
        match_id = str(observation["match_id"])
        decision_id = int(observation["decision_id"])
        seat = int(observation["seat"])
        obs_hash = observation_hash(observation)
        request_id = f"{match_id}:{decision_id}:{seat}"
        self._send(
            {
                "schema": _AGENT_REQUEST_SCHEMA,
                "type": "act",
                "request_id": request_id,
                "decision_id": decision_id,
                "observation_hash": obs_hash,
                "observation": observation,
            }
        )
        response = self._receive(self.timeout_s)
        parsed = AgentResponse.from_mapping(
            response,
            expected_request_id=request_id,
            expected_decision_id=decision_id,
            expected_observation_hash=obs_hash,
            resolution=ActionResolution.tile_center(),
        )
        self.last_telemetry = parsed.telemetry
        action = response["action"]
        if not isinstance(action, dict):
            raise ValueError("agent response action must be a JSON object")
        return action

    def finish(self, result: dict[str, Any]) -> None:
        """Send a seat-scoped match result to the worker before shutdown."""
        if self._process is None:
            return
        payload = {
            **result,
            "agent": self.name,
            "seat": int(self._match_info.get("seat", -1)),
        }
        self._send(
            {
                "schema": _AGENT_EVENT_SCHEMA,
                "type": "end",
                "result": payload,
            }
        )

    def abort_pending(self) -> None:
        """Terminate the worker immediately when the shared runner deadline expires."""
        self._terminate()

    def _terminate(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self.shutdown_timeout_s)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            try:
                self._send({"schema": _AGENT_EVENT_SCHEMA, "type": "close"})
            except Exception:
                pass
            try:
                process.wait(timeout=self.shutdown_timeout_s)
            except subprocess.TimeoutExpired:
                self._terminate()
                return
        self._process = None
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
