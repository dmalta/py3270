from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from py3270 import Terminal
from py3270.terminal import run_sync
from py3270.types import (
    ConnectionState,
    EmulatorMode,
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


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def make_mock_process() -> MagicMock:
    """Return a mock subprocess whose stdout blocks forever (never produces EOF).

    Tests inject responses directly via inject_response() which calls
    handle_response() on the CommandQueue, bypassing the read loop entirely.
    Blocking stdout prevents _read_loop from stopping the queue prematurely.
    """
    proc = MagicMock()
    proc.stdin = AsyncMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    proc.stdout = AsyncMock()

    async def _blocking_read(n: int) -> bytes:  # pragma: no cover
        await asyncio.sleep(9_999)
        return b""

    proc.stdout.read = _blocking_read
    proc.terminate = MagicMock()
    proc.wait = AsyncMock(return_value=0)
    proc.returncode = None
    return proc


@pytest.fixture
def mock_process() -> MagicMock:
    return make_mock_process()


@pytest.fixture
async def running_terminal(mock_process: MagicMock):
    """Terminal with a mocked process; inject responses via inject_response()."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        t = Terminal()
        await t.start()
        yield t
        await t.stop()


def inject_response(terminal: Terminal, response: TerminalResponse) -> None:
    """Simulate a response arriving from s3270 stdout by resolving the in-flight future."""
    assert terminal._command_queue is not None
    terminal._command_queue.handle_response(response)


def _ok(data: str = "", status: str = "") -> TerminalResponse:
    return TerminalResponse(ok=True, data=data, status=status, raw=[])


# ---------------------------------------------------------------------------
# T10: Lifecycle tests
# ---------------------------------------------------------------------------


async def test_start_spawns_process(mock_process: MagicMock) -> None:
    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        t = Terminal()
        await t.start()
        mock_exec.assert_called_once()
        assert mock_exec.call_args.args[0] == "s3270"
        assert t.available() is True
        await t.stop()


async def test_start_is_idempotent(mock_process: MagicMock) -> None:
    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        t = Terminal()
        await t.start()
        await t.start()  # second call — no-op
        assert mock_exec.call_count == 1
        await t.stop()


async def test_stop_clears_process(mock_process: MagicMock) -> None:
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        t = Terminal()
        await t.start()
        await t.stop()
        assert t.available() is False


async def test_stop_on_unstarted_terminal() -> None:
    t = Terminal()
    await t.stop()  # should not raise


def test_available_false_before_start() -> None:
    t = Terminal()
    assert t.available() is False


async def test_command_before_start_raises() -> None:
    t = Terminal()
    with pytest.raises(RuntimeError, match="not running"):
        await t.command("Query(Host)")


# ---------------------------------------------------------------------------
# T11: Command and query tests
# ---------------------------------------------------------------------------


async def test_command_sends_to_queue(running_terminal: Terminal) -> None:
    task = asyncio.create_task(running_terminal.command("Query(Host)"))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    inject_response(
        running_terminal,
        TerminalResponse(
            ok=True,
            data="mvshost",
            status="U F U N I 2 24 80 0 0 0x0 -",
            raw=[],
        ),
    )
    result = await task
    assert result.ok is True
    assert result.data == "mvshost"


async def test_command_with_custom_timeout(mock_process: MagicMock) -> None:
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        t = Terminal()
        await t.start()
        try:
            with pytest.raises(TimeoutError):
                await t.command("SlowCmd", timeout=50)  # no response → times out
        finally:
            await t.stop()


def test_is_keyboard_lock_truthy_for_non_false() -> None:
    t = Terminal()
    t._last_status_info = StatusInfo(
        keyboard_state=KeyboardState.Locked,
        screen_formatting=ScreenFormatting.Formatted,
        field_protection=FieldProtection.Unprotected,
        connection_state=ConnectionState.NotConnected,
        host=None,
        emulator_mode=EmulatorMode.NotConnected,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=0,
        cursor_col=0,
        window_id="0x0",
        command_execution_time=None,
    )
    assert t.is_(StatusFlag.KeyboardLock) is True


def test_cursor_returns_position() -> None:
    t = Terminal()
    t._last_status_info = StatusInfo(
        keyboard_state=KeyboardState.Unlocked,
        screen_formatting=ScreenFormatting.Formatted,
        field_protection=FieldProtection.Unprotected,
        connection_state=ConnectionState.Connected,
        host="h",
        emulator_mode=EmulatorMode.Mode3270,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=5,
        cursor_col=10,
        window_id="0x0",
        command_execution_time=None,
    )
    assert t.cursor() == ScreenPosition(5, 10)


def test_screen_size() -> None:
    t = Terminal()
    t._last_status_info = StatusInfo(
        keyboard_state=KeyboardState.Unlocked,
        screen_formatting=ScreenFormatting.Formatted,
        field_protection=FieldProtection.Unprotected,
        connection_state=ConnectionState.NotConnected,
        host=None,
        emulator_mode=EmulatorMode.NotConnected,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=0,
        cursor_col=0,
        window_id="0x0",
        command_execution_time=None,
    )
    assert t.screen_size() == ScreenSize(24, 80)


# ---------------------------------------------------------------------------
# T12: Connectivity tests
# ---------------------------------------------------------------------------


async def test_connect_builds_simple_address(running_terminal: Terminal) -> None:
    task = asyncio.create_task(running_terminal.connect("mvshost", 23))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    inject_response(
        running_terminal,
        _ok(status="U F U C(mvshost:23) I 2 24 80 0 0 0x0 -"),
    )
    result = await task
    assert result.ok is True
    assert running_terminal._connected is True


async def test_connect_with_mode_and_lu(running_terminal: Terminal) -> None:
    task = asyncio.create_task(
        running_terminal.connect(
            "mvshost", 23, mode=TerminalMode.SuppressExtendedDS, lu_name="LU001"
        )
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    inject_response(
        running_terminal,
        _ok(status="U F U C(S:LU001@mvshost:23) I 2 24 80 0 0 0x0 -"),
    )
    await task
    assert running_terminal._connected is True


async def test_disconnect_when_not_connected() -> None:
    t = Terminal()
    t._connected = False
    result = await t.disconnect()
    assert result.ok is True  # synthetic response, no command sent


async def test_disconnect_when_connected(running_terminal: Terminal) -> None:
    running_terminal._connected = True
    task = asyncio.create_task(running_terminal.disconnect())
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    inject_response(running_terminal, _ok(status="U F U N N 2 24 80 0 0 0x0 -"))
    result = await task
    assert result.ok is True
    assert running_terminal._connected is False


# ---------------------------------------------------------------------------
# T13: Screen / read / write / check tests
# ---------------------------------------------------------------------------


def test_read_basic() -> None:
    t = Terminal()
    t._screen_buffer = ["HELLO WORLD         ", "SECOND LINE         "]
    assert t.read(1, 1, 5) == "HELLO"
    assert t.read(1, 7, 5) == "WORLD"


def test_read_trims_by_default() -> None:
    t = Terminal()
    t._screen_buffer = ["HELLO     "]
    assert t.read(1, 1, 10) == "HELLO"


def test_read_no_trim() -> None:
    t = Terminal()
    t._screen_buffer = ["HELLO     "]
    assert t.read(1, 1, 10, trim=False) == "HELLO     "


def test_read_out_of_bounds_row() -> None:
    t = Terminal()
    t._screen_buffer = ["LINE1"]
    assert t.read(5, 1, 5) == ""


def test_read_row_zero_returns_empty() -> None:
    t = Terminal()
    t._screen_buffer = ["LINE1"]
    assert t.read(0, 1, 5) == ""


def test_check_true() -> None:
    t = Terminal()
    t._screen_buffer = ["READY               "]
    assert t.check("READY", 1, 1) is True


def test_check_false() -> None:
    t = Terminal()
    t._screen_buffer = ["BUSY                "]
    assert t.check("READY", 1, 1) is False


def test_screen_join() -> None:
    t = Terminal()
    t._screen_buffer = ["LINE1", "LINE2"]
    assert t.screen() == "LINE1\nLINE2"


def test_get_screen_buffer_returns_copy() -> None:
    t = Terminal()
    t._screen_buffer = ["A", "B"]
    buf = t.get_screen_buffer()
    buf.append("C")
    assert len(t._screen_buffer) == 2  # original not modified


async def test_write_truncates_to_length(running_terminal: Terminal) -> None:
    results: list[str] = []

    async def capture_command(cmd: str, **kw: object) -> TerminalResponse:
        results.append(cmd)
        inject_response(running_terminal, _ok())
        return _ok()

    running_terminal.command = capture_command  # type: ignore[method-assign]
    await running_terminal.write("HELLOWORLD", 3, 5, length=5)
    assert any("HELLO" in r for r in results)


# ---------------------------------------------------------------------------
# T14: Text / input helper tests
# ---------------------------------------------------------------------------


async def test_pf_valid(running_terminal: Terminal) -> None:
    for n in [1, 12, 24]:
        task = asyncio.create_task(running_terminal.pf(n))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        inject_response(running_terminal, _ok())
        await task


async def test_pf_out_of_range() -> None:
    t = Terminal()
    with pytest.raises(ValueError, match="PF"):
        await t.pf(0)
    with pytest.raises(ValueError, match="PF"):
        await t.pf(25)


async def test_pa_valid(running_terminal: Terminal) -> None:
    for n in [1, 2, 3]:
        task = asyncio.create_task(running_terminal.pa(n))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        inject_response(running_terminal, _ok())
        await task


async def test_pa_out_of_range() -> None:
    t = Terminal()
    with pytest.raises(ValueError, match="PA"):
        await t.pa(0)
    with pytest.raises(ValueError, match="PA"):
        await t.pa(4)


async def test_string_validates_escape() -> None:
    t = Terminal()
    with pytest.raises(ValueError):
        await t.string(r"\z invalid")


# ---------------------------------------------------------------------------
# T15: Wait helper tests
# ---------------------------------------------------------------------------


async def test_wait_for_global_mode_found(running_terminal: Terminal) -> None:
    running_terminal._screen_buffer = ["READY TO PROCEED"]

    async def noop_refresh() -> TerminalResponse:
        return _ok(data="READY TO PROCEED")

    running_terminal.refresh = noop_refresh  # type: ignore[method-assign]
    result = await running_terminal.wait_for("READY", timeout=1000)
    assert result is True


async def test_wait_for_positional_mode_found(running_terminal: Terminal) -> None:
    running_terminal._screen_buffer = ["HELLO WORLD         "]

    async def noop_refresh() -> TerminalResponse:
        return _ok()

    running_terminal.refresh = noop_refresh  # type: ignore[method-assign]
    result = await running_terminal.wait_for("HELLO", row=1, col=1, timeout=500)
    assert result is True


async def test_wait_for_timeout_returns_false(running_terminal: Terminal) -> None:
    running_terminal._screen_buffer = ["NOTHING HERE"]

    async def noop_refresh() -> TerminalResponse:
        return _ok()

    running_terminal.refresh = noop_refresh  # type: ignore[method-assign]
    result = await running_terminal.wait_for("XYZZY", timeout=150)
    assert result is False


async def test_wait_for_partial_row_col_raises() -> None:
    t = Terminal()
    with pytest.raises(ValueError, match="both"):
        await t.wait_for("text", row=3)  # col missing
    with pytest.raises(ValueError, match="both"):
        await t.wait_for("text", col=5)  # row missing


async def test_wait_for_timeout_clamped() -> None:
    """Negative timeout clamped to 0 — returns False immediately."""
    t = Terminal()
    t._screen_buffer = []

    async def noop(*a: object, **kw: object) -> TerminalResponse:
        return _ok()

    t.refresh = noop  # type: ignore[method-assign]
    result = await t.wait_for("X", timeout=-1000)
    assert result is False


# ---------------------------------------------------------------------------
# T16: run_sync tests
# ---------------------------------------------------------------------------


def test_run_sync_executes_coroutine() -> None:
    async def sample() -> int:
        return 42

    result = run_sync(sample)
    assert result == 42


def test_run_sync_raises_in_running_loop() -> None:
    async def inner() -> None:
        async def dummy() -> None:
            pass

        with pytest.raises(RuntimeError, match="running event loop"):
            run_sync(dummy)

    asyncio.run(inner())
