from __future__ import annotations

import time

import pytest

from py3270 import SessionState, Terminal, TerminalOptions
from py3270._parser import parse_status
from tests.integration.conftest import DEMO_HOST, DEMO_PORT


pytestmark = pytest.mark.integration


def test_s3270_binary_available(s3270_path: str) -> None:
    assert s3270_path


# =====================================================================
# T2: Lifecycle smoke tests
# =====================================================================


def test_start_stop(terminal) -> None:
    assert terminal.available() is True
    assert terminal.state == SessionState.Started


def test_start_stop_three_times(s3270_path: str) -> None:
    for _ in range(3):
        terminal = Terminal(TerminalOptions(executable=s3270_path, timeout=5_000))
        terminal.start()
        assert terminal.available() is True
        terminal.stop()
        assert terminal.available() is False


def test_stop_on_unstarted_does_not_raise() -> None:
    terminal = Terminal()
    terminal.stop()


# =====================================================================
# T3: Raw command and status tests
# =====================================================================


def test_query_host_unconnected(terminal) -> None:
    response = terminal.command("Query(Host)")
    assert isinstance(response.ok, bool)


def test_command_returns_parseable_status(terminal) -> None:
    response = terminal.command("Query(Model)")
    if response.status:
        info = parse_status(response.status)
        assert info is not None
        assert info.rows >= 24
        assert info.cols >= 80


def test_command_error_response(terminal) -> None:
    response = terminal.command("Disconnect")
    assert isinstance(response.ok, bool)


# =====================================================================
# T4: Screen cache integration tests
# =====================================================================


def test_refresh_returns_screen_buffer(terminal) -> None:
    terminal.refresh()
    buffer = terminal.get_screen_buffer()
    assert isinstance(buffer, list)
    assert len(buffer) > 0


def test_screen_is_string(terminal) -> None:
    terminal.refresh()
    screen = terminal.screen()
    assert isinstance(screen, str)


def test_screen_size_after_command(terminal) -> None:
    terminal.command("Query(Model)")
    size = terminal.screen_size()
    if size is not None:
        assert size.rows >= 24
        assert size.cols >= 80


# =====================================================================
# T5: Wait helper integration tests
# =====================================================================


def test_wait_for_not_found_returns_false(terminal) -> None:
    terminal.refresh()
    start = time.monotonic()
    result = terminal.wait_for("XYZZY_NOT_ON_SCREEN_EVER", timeout=300)
    elapsed = time.monotonic() - start
    assert result is False
    assert elapsed < 1.0


def test_wait_unlock_completes_on_idle(terminal) -> None:
    result = terminal.wait_unlock(timeout=2_000)
    # Verify that wait_unlock returns a response (may be ok or not depending on state)
    assert isinstance(result.ok, bool)


def test_wait_ready_completes_on_idle(terminal) -> None:
    terminal.wait_ready(timeout=2_000)


# =====================================================================
# T6: Optional live-host tests
# =====================================================================


@pytest.mark.skipif(not DEMO_HOST, reason="PY3270_DEMO_HOST not set")
def test_live_connect_and_disconnect(terminal) -> None:
    connect_response = terminal.connect(DEMO_HOST, DEMO_PORT)
    assert connect_response.ok is True

    terminal.refresh()
    buffer = terminal.get_screen_buffer()
    assert any(line.strip() for line in buffer)

    disconnect_response = terminal.disconnect()
    assert disconnect_response.ok is True


# =====================================================================
# T7: SessionManager smoke test
# =====================================================================


def test_session_manager_create_and_close(session_manager, s3270_path: str) -> None:
    options = TerminalOptions(executable=s3270_path, timeout=5_000)
    first_id = session_manager.create_session(options, start=True)
    second_id = session_manager.create_session(options, start=True)

    first = session_manager.get_session(first_id)
    second = session_manager.get_session(second_id)

    assert first_id != second_id
    assert first.available() is True
    assert second.available() is True
    assert first.state == SessionState.Started
    assert second.state == SessionState.Started

    session_manager.close_all()
    assert first.available() is False
    assert second.available() is False
