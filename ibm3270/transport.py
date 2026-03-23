from __future__ import annotations

__docformat__ = "google"

import queue
import subprocess
import threading
import time
from typing import IO

from ibm3270.errors import (
    SessionBusyError,
    SessionDisconnectedError,
    SessionProcessError,
    SessionTimeoutError,
)
from ibm3270.types import TerminalResponse

_EOF = object()


def _build_response(lines: list[str], terminal_line: str) -> TerminalResponse:
    if not lines:
        status = ""
        data_lines: list[str] = []
    else:
        status = lines[-1]
        data_lines = lines[:-1]

    stripped = [line[6:] if line.startswith("data: ") else line for line in data_lines]
    return TerminalResponse(
        ok=(terminal_line == "ok"),
        data="\n".join(stripped),
        status=status,
        raw=lines + [terminal_line],
    )


class _StdoutReader(threading.Thread):
    def __init__(
        self,
        stream: IO[str],
        line_queue: queue.Queue[str | object],
    ) -> None:
        super().__init__(name="s3270-stdout-reader", daemon=True)
        self._stream = stream
        self._line_queue = line_queue

    def run(self) -> None:
        while True:
            line = self._stream.readline()
            if line == "":
                self._line_queue.put(_EOF)
                return
            self._line_queue.put(line.rstrip("\r\n"))


class Transport:
    """Low-level process transport for one s3270 session.

    Manages the s3270 subprocess, its stdin/stdout pipe, and the lock that
    prevents concurrent in-flight commands.

    Args:
        default_timeout_ms: Timeout in milliseconds used when callers do not
            supply an explicit timeout to `execute`.
    """

    def __init__(self, *, default_timeout_ms: int) -> None:
        self._default_timeout_ms = default_timeout_ms
        self._process: subprocess.Popen[str] | None = None
        self._line_queue: queue.Queue[str | object] = queue.Queue()
        self._reader: _StdoutReader | None = None
        self._inflight_lock = threading.Lock()
        self._stopped = False

    def available(self) -> bool:
        """Return ``True`` if the s3270 process is running."""
        return self._process is not None and self._process.poll() is None

    def pid(self) -> int | None:
        """Return the PID of the s3270 process, or ``None`` if not started."""
        if self._process is None:
            return None
        return self._process.pid

    def start(self, executable: str, args: list[str]) -> None:
        """Launch the s3270 process. No-op if already running.

        Args:
            executable: Path or name of the s3270 binary.
            args: Extra command-line arguments (e.g. ``["-model", "3279-2"]``).
        """
        if self.available():
            return

        cmd = [executable, "-script", *args]
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert self._process.stdout is not None
        self._line_queue = queue.Queue()
        self._reader = _StdoutReader(self._process.stdout, self._line_queue)
        self._reader.start()
        self._stopped = False

    def stop(self) -> None:
        """Terminate the s3270 process and clean up resources."""
        self._stopped = True
        if self._process is None:
            return

        try:
            if self._process.stdin is not None:
                self._process.stdin.close()
        except Exception:
            pass

        try:
            if self._process.poll() is None:
                self._process.terminate()
                self._process.wait(timeout=2)
        except Exception:
            try:
                self._process.kill()
                self._process.wait(timeout=2)
            except Exception:
                pass

        if self._reader is not None:
            self._reader.join(timeout=1)
            self._reader = None

        self._process = None

    def execute(self, command: str, *, timeout: int | None = None) -> TerminalResponse:
        """Send *command* to s3270 and return the response.

        Args:
            command: The raw s3270 command string.
            timeout: Timeout in milliseconds. Falls back to *default_timeout_ms* if ``None``.

        Returns:
            A `TerminalResponse` with `ok`, `data`, and `status`.

        Raises:
            SessionBusyError: If another command is already in flight.
            SessionTimeoutError: If no response arrives before the timeout.
            SessionProcessError: If the s3270 process terminates unexpectedly.
        """
        if self._stopped:
            raise RuntimeError("Transport is stopped")
        if not self._inflight_lock.acquire(blocking=False):
            raise SessionBusyError("Session already has an in-flight operation")

        try:
            self._send_raw(command)
            effective_timeout = timeout if timeout is not None else self._default_timeout_ms
            return self._read_response(effective_timeout)
        finally:
            self._inflight_lock.release()

    def _assert_running(self) -> None:
        if not self.available():
            raise SessionDisconnectedError("Terminal is not running")

    def _send_raw(self, command: str) -> None:
        self._assert_running()
        assert self._process is not None
        assert self._process.stdin is not None
        try:
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()
        except OSError as exc:
            raise SessionProcessError(f"Failed to send command: {command}") from exc

    def _read_response(self, timeout_ms: int) -> TerminalResponse:
        deadline = time.monotonic() + (timeout_ms / 1000)
        lines: list[str] = []

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SessionTimeoutError("Command timeout")
            try:
                item = self._line_queue.get(timeout=remaining)
            except queue.Empty as exc:
                raise SessionTimeoutError("Command timeout") from exc

            if item is _EOF:
                self._stopped = True
                raise SessionProcessError("s3270 process terminated unexpectedly")

            line = str(item)
            if line == "ok" or line.startswith("error"):
                return _build_response(lines, line)
            lines.append(line)
