"""Persistent JSON-lines subprocess adapter for external benchmark agents."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from royalebench.observations import observation_hash


class AgentProcessError(RuntimeError):
    """An external agent process violated the JSON-lines protocol or exited unexpectedly."""


class JsonlSubprocessAgent:
    """Run an external agent behind a persistent, timeout-enforced JSON-lines process.

    The child receives one JSON object per stdin line:
      * reset: {"type": "reset", "match_info": {...}}
      * act: request identity plus the full FAIR observation
      * close: {"type": "close"}

    Only act requests produce stdout responses. A response must echo request_id,
    decision_id and observation_hash and contain an ActionV1 object. Child diagnostics
    belong on stderr; stdout is reserved for protocol responses.
    """

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        timeout_s: float = 120.0,
        shutdown_timeout_s: float = 2.0,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("agent name must be a non-empty string")
        if not command or any(not str(part) for part in command):
            raise ValueError("subprocess command must contain non-empty arguments")
        if timeout_s <= 0 or shutdown_timeout_s <= 0:
            raise ValueError("agent timeouts must be positive")

        self.name = name
        self.command = tuple(str(part) for part in command)
        self.timeout_s = float(timeout_s)
        self.shutdown_timeout_s = float(shutdown_timeout_s)
        self.cwd = None if cwd is None else str(Path(cwd))
        self.env = None if env is None else {str(k): str(v) for k, v in env.items()}
        self.last_telemetry: dict[str, Any] | None = None
        self._match_info: dict[str, Any] = {}
        self._process: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[str | None | Exception] = queue.Queue()
        self._write_lock = threading.Lock()
        self._reader: threading.Thread | None = None

    def set_timeout(self, timeout_s: float) -> None:
        """Align the child response deadline with the enclosing MatchRunner watchdog."""
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.timeout_s = float(timeout_s)

    def _start(self) -> None:
        child_env = os.environ.copy()
        if self.env:
            child_env.update(self.env)
        try:
            process = subprocess.Popen(
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
            raise AgentProcessError(
                f"could not start agent {self.name!r}: {exc}"
            ) from exc
        if process.stdin is None or process.stdout is None:
            process.kill()
            raise AgentProcessError("agent process did not expose stdin and stdout pipes")

        self._responses = queue.Queue()
        self._process = process
        self._reader = threading.Thread(
            target=self._read_stdout,
            args=(process.stdout,),
            name=f"royalebench-{self.name}-stdout",
            daemon=True,
        )
        self._reader.start()

    def _read_stdout(self, stream) -> None:
        try:
            for line in stream:
                self._responses.put(line.rstrip("\r\n"))
        except Exception as exc:
            self._responses.put(exc)
        finally:
            self._responses.put(None)

    def _send(self, payload: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            code = None if process is None else process.poll()
            raise AgentProcessError(
                f"agent {self.name!r} is not running (exit code: {code})"
            )
        try:
            encoded = json.dumps(
                payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
            with self._write_lock:
                process.stdin.write(encoded + "\n")
                process.stdin.flush()
        except (OSError, TypeError, ValueError) as exc:
            self._stop_process()
            raise AgentProcessError(f"could not write to agent {self.name!r}: {exc}") from exc

    def reset(self, match_info: dict[str, Any]) -> None:
        """Start a fresh process for an episode and send public match configuration."""
        self.close()
        self._match_info = dict(match_info)
        self.last_telemetry = None
        self._start()
        self._send({"type": "reset", "match_info": self._match_info})

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Send one observation and wait for its identity-bound action response."""
        if self._process is None:
            raise AgentProcessError("agent reset() must be called before act()")

        match_id = observation.get("match_id")
        decision_id = observation.get("decision_id")
        seat = observation.get("seat")
        if not isinstance(match_id, str) or not match_id:
            raise AgentProcessError("observation has no valid match_id")
        if isinstance(decision_id, bool) or not isinstance(decision_id, int) or decision_id < 0:
            raise AgentProcessError("observation has no valid decision_id")
        if isinstance(seat, bool) or not isinstance(seat, int) or seat not in (0, 1):
            raise AgentProcessError("observation has no valid seat")
        expected_seat = self._match_info.get("seat")
        if expected_seat is not None and int(expected_seat) != seat:
            raise AgentProcessError(
                f"agent {self.name!r} was reset for seat {expected_seat}, got seat {seat}"
            )

        request_id = f"{match_id}:{decision_id}:{seat}"
        digest = observation_hash(observation)
        self._send(
            {
                "type": "act",
                "request_id": request_id,
                "decision_id": decision_id,
                "observation_hash": digest,
                "observation": observation,
            }
        )

        try:
            line = self._responses.get(timeout=self.timeout_s)
        except queue.Empty as exc:
            self._stop_process()
            raise TimeoutError(
                f"agent {self.name!r} exceeded its {self.timeout_s:g}s response deadline"
            ) from exc

        if isinstance(line, Exception):
            self._stop_process()
            raise AgentProcessError(f"could not read agent {self.name!r} response: {line}") from line
        if line is None:
            process = self._process
            code = None if process is None else process.poll()
            self._stop_process()
            raise AgentProcessError(
                f"agent {self.name!r} exited before responding (exit code: {code})"
            )
        if not line:
            self._stop_process()
            raise AgentProcessError(f"agent {self.name!r} wrote an empty stdout line")

        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            self._stop_process()
            raise AgentProcessError(
                f"agent {self.name!r} wrote non-JSON stdout; keep diagnostics on stderr"
            ) from exc
        if not isinstance(response, dict):
            self._stop_process()
            raise AgentProcessError("agent response must be a JSON object")

        required = {"request_id", "decision_id", "observation_hash", "action"}
        allowed = required | {"telemetry"}
        if required - set(response) or set(response) - allowed:
            self._stop_process()
            raise AgentProcessError(
                "agent response fields must be request_id, decision_id, "
                "observation_hash, action, and optional telemetry"
            )
        if response["request_id"] != request_id:
            self._stop_process()
            raise AgentProcessError("agent response request_id is stale or mismatched")
        if response["decision_id"] != decision_id:
            self._stop_process()
            raise AgentProcessError("agent response decision_id is stale or mismatched")
        if response["observation_hash"] != digest:
            self._stop_process()
            raise AgentProcessError("agent response observation_hash is stale or mismatched")
        action = response["action"]
        if not isinstance(action, dict):
            self._stop_process()
            raise AgentProcessError("agent response action must be a JSON object")
        telemetry = response.get("telemetry")
        if telemetry is not None and not isinstance(telemetry, dict):
            self._stop_process()
            raise AgentProcessError("agent telemetry must be a JSON object")
        self.last_telemetry = telemetry
        return action

    def _stop_process(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        for pipe in (process.stdin, process.stdout):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self.shutdown_timeout_s)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def close(self) -> None:
        """Ask the child to exit, then terminate it if it ignores the close message."""
        process = self._process
        if process is None:
            return
        if process.poll() is None and process.stdin is not None:
            try:
                self._send({"type": "close"})
            except AgentProcessError:
                pass
        self._stop_process()
        self._match_info = {}
        self.last_telemetry = None
