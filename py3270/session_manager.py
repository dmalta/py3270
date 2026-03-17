from __future__ import annotations

from threading import Lock
from uuid import uuid4

from py3270.terminal import Terminal
from py3270.types import TerminalOptions


class SessionManager:
    """Manage multiple isolated terminal sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, Terminal] = {}
        self._lock = Lock()

    def create_session(self, options: TerminalOptions | None = None, *, start: bool = False) -> str:
        session_id = str(uuid4())
        session = Terminal(options=options, session_id=session_id)
        if start:
            session.start()
        with self._lock:
            self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Terminal:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session id: {session_id}")
        return session

    def close_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            session.stop()

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.stop()

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())
