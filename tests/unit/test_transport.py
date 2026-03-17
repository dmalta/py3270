from __future__ import annotations

import queue
import threading
import time
from collections.abc import Generator
from unittest.mock import patch

import pytest

from py3270.errors import SessionBusyError, SessionProcessError, SessionTimeoutError
from py3270.transport import _EOF, Transport


class _MockStdin:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, text: str) -> None:
        self.writes.append(text)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None


class _BlockingStdout:
    def __init__(self) -> None:
        self._lines: queue.Queue[str | None] = queue.Queue()

    def readline(self) -> str:
        line = self._lines.get()
        if line is None:
            return ""
        return line

    def close_with_eof(self) -> None:
        self._lines.put(None)


class _MockProcess:
    def __init__(self) -> None:
        self.stdin = _MockStdin()
        self.stdout = _BlockingStdout()
        self.pid = 777
        self._alive = True

    def poll(self) -> int | None:
        return None if self._alive else 0

    def terminate(self) -> None:
        self._alive = False
        self.stdout.close_with_eof()

    def wait(self, timeout: float | None = None) -> int:
        self._alive = False
        return 0

    def kill(self) -> None:
        self.terminate()


@pytest.fixture
def running_transport() -> Generator[Transport, None, None]:
    process = _MockProcess()
    with patch("subprocess.Popen", return_value=process):
        transport = Transport(default_timeout_ms=250)
        transport.start("s3270", [])
        try:
            yield transport
        finally:
            transport.stop()


def _inject_ok(transport: Transport, data: str = "", status: str = "U F U N I 2 24 80 0 0 0x0 -") -> None:
    if data:
        transport._line_queue.put(f"data: {data}")
    transport._line_queue.put(status)
    transport._line_queue.put("ok")


def test_execute_round_trip(running_transport: Transport) -> None:
    _inject_ok(running_transport, data="host")
    result = running_transport.execute("Query(Host)")

    assert result.ok is True
    assert result.data == "host"


def test_execute_custom_timeout(running_transport: Transport) -> None:
    with pytest.raises(SessionTimeoutError):
        running_transport.execute("Wait(Output)", timeout=10)


def test_stop_rejects_new_execute(running_transport: Transport) -> None:
    running_transport.stop()
    with pytest.raises(RuntimeError, match="stopped"):
        running_transport.execute("Query(Host)")


def test_process_death_raises(running_transport: Transport) -> None:
    running_transport._line_queue.put(_EOF)
    with pytest.raises(SessionProcessError):
        running_transport.execute("Query(Host)")


def test_one_in_flight_busy_error(running_transport: Transport) -> None:
    errors: list[Exception] = []

    def first_call() -> None:
        try:
            running_transport.execute("first", timeout=1000)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    t = threading.Thread(target=first_call)
    t.start()
    time.sleep(0.05)

    with pytest.raises(SessionBusyError):
        running_transport.execute("second")

    _inject_ok(running_transport, data="done")
    t.join(timeout=1)
    assert not errors
