from __future__ import annotations

__docformat__ = "google"

from threading import Lock
from uuid import uuid4

from ibm3270.terminal import Terminal
from ibm3270.types import TerminalOptions


class SessionManager:
    """Manage multiple isolated terminal sessions.

    Thread-safe registry of `Terminal` instances keyed
    by auto-generated UUID session IDs.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Terminal] = {}
        self._lock = Lock()

    def create_session(self, options: TerminalOptions | None = None, *, start: bool = False) -> str:
        """Create a new terminal session and register it.

        Args:
            options: Configuration for the underlying s3270 process. Defaults to `TerminalOptions()`.
            start: If `True`, call `Terminal.start` immediately.

        Returns:
            The new session ID (UUID string).
        """
        session_id = str(uuid4())
        session = Terminal(options=options, session_id=session_id)
        if start:
            session.start()
        with self._lock:
            self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Terminal:
        """Retrieve a session by ID.

        Args:
            session_id: The UUID string returned by `create_session`.

        Returns:
            The `Terminal` for that session.

        Raises:
            KeyError: If *session_id* is not registered.
        """
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session id: {session_id}")
        return session

    def close_session(self, session_id: str) -> None:
        """Stop and remove a session.

        Args:
            session_id: The UUID string of the session to close.

        No-op if the session ID is unknown.
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            session.stop()

    def close_all(self) -> None:
        """Stop and remove all registered sessions."""
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.stop()

    def list_sessions(self) -> list[str]:
        """Return the IDs of all registered sessions."""
        with self._lock:
            return list(self._sessions.keys())
