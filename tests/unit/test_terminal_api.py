from __future__ import annotations

import queue
import threading
import time
from collections.abc import Generator
from typing import cast
from unittest.mock import patch

import pytest

from py3270 import (
    SessionBusyError,
    SessionProcessError,
    SessionState,
    SessionTimeoutError,
    Terminal,
)
from py3270 import transport as transport_module
from py3270 import field
from py3270.types import TerminalOptions
from py3270.types import (
    ConnectionState,
    EmulatorMode,
    FieldDefinition,
    FieldProtection,
    KeyboardState,
    ScreenFormatting,
    ScreenPosition,
    ScreenSize,
    StatusFlag,
    StatusInfo,
    TerminalMode,
    TerminalResponse,
)


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
        self.pid = 1234
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
def running_terminal() -> Generator[Terminal, None, None]:
    proc = _MockProcess()
    with patch("subprocess.Popen", return_value=proc):
        terminal = Terminal()
        terminal.start()
        try:
            yield terminal
        finally:
            terminal.stop()


def _inject_response(terminal: Terminal, response: TerminalResponse) -> None:
    lines = response.raw[:-1] if response.raw else []
    terminal_line = "ok" if response.ok else f"error {response.data}"
    line_queue = terminal._transport._line_queue
    for line in lines:
        line_queue.put(line)
    line_queue.put(terminal_line)


def _ok(data: str = "", status: str = "") -> TerminalResponse:
    effective_status = status or "U F U N I 2 24 80 0 0 0x0 -"
    raw: list[str] = []
    if data:
        raw.extend([f"data: {line}" for line in data.splitlines()])
    raw.append(effective_status)
    raw.append("ok")
    return TerminalResponse(ok=True, data=data, status=effective_status, raw=raw)


def test_start_and_stop() -> None:
    proc = _MockProcess()
    with patch("subprocess.Popen", return_value=proc) as popen:
        terminal = Terminal()
        terminal.start()

        assert popen.call_count == 1
        assert terminal.available() is True
        assert terminal.state == SessionState.Started

        terminal.stop()
        assert terminal.available() is False
        assert terminal.state == SessionState.Stopped

        command = popen.call_args.args[0]
        assert command[:3] == ["s3270", "-script", "-model"]
        assert command[3] == "3279-2"


def test_start_is_idempotent() -> None:
    proc = _MockProcess()
    with patch("subprocess.Popen", return_value=proc) as popen:
        terminal = Terminal()
        terminal.start()
        terminal.start()
        assert popen.call_count == 1
        terminal.stop()


def test_start_preserves_explicit_model_arg() -> None:
    proc = _MockProcess()
    options = TerminalOptions(args=["-model", "3279-4"])
    with patch("subprocess.Popen", return_value=proc) as popen:
        terminal = Terminal(options)
        terminal.start()

        command = popen.call_args.args[0]
        assert command == ["s3270", "-script", "-model", "3279-4"]

        terminal.stop()


def test_start_preserves_explicit_xrm_model() -> None:
    proc = _MockProcess()
    options = TerminalOptions(args=["-xrm", "s3270.model: 3278-5"])
    with patch("subprocess.Popen", return_value=proc) as popen:
        terminal = Terminal(options)
        terminal.start()

        command = popen.call_args.args[0]
        assert command == ["s3270", "-script", "-xrm", "s3270.model: 3278-5"]

        terminal.stop()


def test_command_before_start_raises() -> None:
    terminal = Terminal()
    with pytest.raises(Exception, match="not running"):
        terminal.command("Query(Host)")


def test_command_round_trip(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok("mvshost", "U F U N I 2 24 80 0 0 0x0 -"))
    result = running_terminal.command("Query(Host)")

    assert result.ok is True
    assert result.data == "mvshost"
    process = cast(_MockProcess, running_terminal._transport._process)
    assert process.stdin.writes[-1] == "Query(Host)\n"


def test_timeout_raises_session_timeout(running_terminal: Terminal) -> None:
    with pytest.raises(SessionTimeoutError):
        running_terminal.command("SlowCmd", timeout=25)


def test_process_death_raises_session_process_error(running_terminal: Terminal) -> None:
    running_terminal._transport._line_queue.put(transport_module._EOF)
    with pytest.raises(SessionProcessError):
        running_terminal.command("Query(Host)")


def test_one_in_flight_busy_error(running_terminal: Terminal) -> None:
    errors: list[Exception] = []

    def first_call() -> None:
        try:
            running_terminal.command("Query(Host)", timeout=1000)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    t = threading.Thread(target=first_call)
    t.start()
    time.sleep(0.05)

    with pytest.raises(SessionBusyError):
        running_terminal.command("Query(Host)")

    _inject_response(running_terminal, _ok("mvshost", "U F U N I 2 24 80 0 0 0x0 -"))
    t.join(timeout=1)
    assert not errors


def test_connect_disconnect_state_transitions(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok(status="U F U C(mvshost:23) I 2 24 80 0 0 0x0 -"))
    response = running_terminal.connect("mvshost", 23)
    assert response.ok is True
    assert running_terminal.state == SessionState.Connected

    _inject_response(running_terminal, _ok(status="U F U N N 2 24 80 0 0 0x0 -"))
    response = running_terminal.disconnect()
    assert response.ok is True
    assert running_terminal.state == SessionState.Disconnected


def test_connect_builds_mode_and_lu(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok(status="U F U C(S:LU001@mvshost:23) I 2 24 80 0 0 0x0 -"))
    running_terminal.connect("mvshost", 23, mode=TerminalMode.SuppressExtendedDS, lu_name="LU001")

    process = cast(_MockProcess, running_terminal._transport._process)
    assert process.stdin.writes[-1] == "Connect(S:LU001@mvshost:23)\n"


def test_read_check_and_screen_helpers() -> None:
    t = Terminal()
    t._screen_buffer = ["HELLO WORLD     ", "SECOND          "]

    assert t.read(1, 1, 5) == "HELLO"
    assert t.check("WORLD", 1, 7) is True
    assert t.screen() == "HELLO WORLD     \nSECOND          "
    assert t.get_screen_buffer() == ["HELLO WORLD     ", "SECOND          "]


def test_read_stops_at_end_of_row_without_wrapping() -> None:
    t = Terminal()
    first_row = "".join(str(i % 10) for i in range(80))
    second_row = "X" * 80
    t._screen_buffer = [first_row, second_row]

    # Request past the row boundary and ensure read() does not continue into next row.
    result = t.read(1, 60, 80, trim=False)

    assert first_row.endswith(result)
    assert len(result) == 21
    assert "X" not in result


def test_read_many_parses_number_field() -> None:
    t = Terminal()

    def fake_refresh() -> TerminalResponse:
        t._screen_buffer = ["VAL 123.5"]
        return _ok("VAL 123.5")

    t.refresh = fake_refresh  # type: ignore[method-assign]

    fields = [
        FieldDefinition(row=1, col=1, length=3, type="string"),
        FieldDefinition(row=1, col=5, length=5, type="number"),
    ]
    result = t.read_many(fields)

    assert result["1,1"] == "VAL"
    assert result["1,5"] == pytest.approx(123.5)


def test_read_many_uses_name_when_present() -> None:
    t = Terminal()

    def fake_refresh() -> TerminalResponse:
        t._screen_buffer = ["USER123   456.7"]
        return _ok("USER123   456.7")

    t.refresh = fake_refresh  # type: ignore[method-assign]

    result = t.read_many(
        [
            field(1, 1, 7, name="user_id"),
            field(1, 11, 5, "number", name="amount"),
        ]
    )

    assert result == {"user_id": "USER123", "amount": pytest.approx(456.7)}


def test_read_many_mixes_named_and_positional_keys() -> None:
    t = Terminal()

    def fake_refresh() -> TerminalResponse:
        t._screen_buffer = ["ABC    999 "]
        return _ok("ABC    999 ")

    t.refresh = fake_refresh  # type: ignore[method-assign]

    result = t.read_many(
        [
            field(1, 1, 3, name="code"),
            field(1, 8, 3, "number"),
        ]
    )

    assert result["code"] == "ABC"
    assert result["1,8"] == pytest.approx(999.0)


def test_write_sends_move_then_string(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok())
    _inject_response(running_terminal, _ok())
    running_terminal.write("HELLOWORLD", 3, 5, length=5)

    process = cast(_MockProcess, running_terminal._transport._process)
    assert process.stdin.writes[-2:] == ["MoveCursor(2,4)\n", "String(HELLO)\n"]


def test_pf_and_pa_ranges(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok())
    running_terminal.pf(1)

    _inject_response(running_terminal, _ok())
    running_terminal.pa(3)

    with pytest.raises(ValueError, match="PF"):
        running_terminal.pf(0)

    with pytest.raises(ValueError, match="PA"):
        running_terminal.pa(4)


def test_wait_for_modes() -> None:
    t = Terminal()
    t._screen_buffer = ["READY NOW"]

    def fake_refresh() -> TerminalResponse:
        return _ok("READY NOW")

    t.refresh = fake_refresh  # type: ignore[method-assign]

    assert t.wait_for("READY", timeout=100) is True
    assert t.wait_for("READY", row=1, col=1, timeout=100) is True


def test_wait_for_invalid_coordinates() -> None:
    t = Terminal()
    with pytest.raises(ValueError, match="both row and col"):
        t.wait_for("X", row=1)


def test_status_getters() -> None:
    t = Terminal()
    t._last_status_info = StatusInfo(
        keyboard_state=KeyboardState.Locked,
        screen_formatting=ScreenFormatting.Formatted,
        field_protection=FieldProtection.Unprotected,
        connection_state=ConnectionState.Connected,
        host="mvshost",
        emulator_mode=EmulatorMode.Mode3270,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=5,
        cursor_col=10,
        window_id="0x0",
        command_execution_time=None,
    )

    assert t.cursor() == ScreenPosition(6, 11)
    assert t.screen_size() == ScreenSize(24, 80)
    assert t.is_(StatusFlag.Formatted) is True
    assert t.is_(StatusFlag.KeyboardLock) is True
    assert t.current_field() == ScreenPosition(6, 11)


def test_move_uses_display_coordinates(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok())
    running_terminal.move(2, 3)

    process = cast(_MockProcess, running_terminal._transport._process)
    assert process.stdin.writes[-1] == "MoveCursor(1,2)\n"


def test_move_rejects_non_display_coordinates(running_terminal: Terminal) -> None:
    with pytest.raises(ValueError, match=">= 1"):
        running_terminal.move(0, 1)


def test_run_workflow(running_terminal: Terminal) -> None:
    _inject_response(running_terminal, _ok("a"))
    _inject_response(running_terminal, _ok("b"))
    responses = running_terminal.run_workflow(["Query(A)", "Query(B)"])

    assert [response.data for response in responses] == ["a", "b"]


def test_multi_session_parallel_safety() -> None:
    proc1 = _MockProcess()
    proc2 = _MockProcess()

    with patch("subprocess.Popen", side_effect=[proc1, proc2]):
        t1 = Terminal(session_id="s1")
        t2 = Terminal(session_id="s2")
        t1.start()
        t2.start()

        result_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        def run_cmd(label: str, terminal: Terminal) -> None:
            response = terminal.command("Query(Host)")
            result_queue.put((label, response.data))

        th1 = threading.Thread(target=run_cmd, args=("s1", t1))
        th2 = threading.Thread(target=run_cmd, args=("s2", t2))
        th1.start()
        th2.start()

        _inject_response(t1, _ok("host1", "U F U N I 2 24 80 0 0 0x0 -"))
        _inject_response(t2, _ok("host2", "U F U N I 2 24 80 0 0 0x0 -"))

        th1.join(timeout=1)
        th2.join(timeout=1)

        outcomes = sorted([result_queue.get(timeout=1), result_queue.get(timeout=1)])
        assert outcomes == [("s1", "host1"), ("s2", "host2")]

        t1.stop()
        t2.stop()
