from __future__ import annotations

import os
import shutil
from collections.abc import Iterator

import pytest

from py3270 import SessionManager, Terminal, TerminalOptions


@pytest.fixture(scope="session", name="s3270_path")
def s3270_executable_path() -> str:
    executable_path = shutil.which("s3270")
    if executable_path is None:
        # Check if s3270 is in the project's bin directory
        project_bin = os.path.join(
            os.path.dirname(__file__), "..", "..", "bin", "s3270.exe"
        )
        if os.path.exists(project_bin):
            executable_path = project_bin
        else:
            pytest.skip(
                "s3270 binary not found on PATH or in bin/; "
                "skipping integration tests"
            )
    return executable_path


@pytest.fixture
def terminal(s3270_path: str) -> Iterator[Terminal]:
    started_terminal = Terminal(
        TerminalOptions(executable=s3270_path, timeout=10_000)
    )
    started_terminal.start()
    try:
        yield started_terminal
    finally:
        if started_terminal.available():
            started_terminal.stop()


@pytest.fixture
def session_manager() -> Iterator[SessionManager]:
    manager = SessionManager()
    try:
        yield manager
    finally:
        manager.close_all()


DEMO_HOST = os.environ.get("PY3270_DEMO_HOST", "")
DEMO_PORT = int(os.environ.get("PY3270_DEMO_PORT", "23"))
