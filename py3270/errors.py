from __future__ import annotations


class SessionError(Exception):
    """Base exception for session-level failures."""


class SessionTimeoutError(SessionError, TimeoutError):
    """Raised when a blocking session operation exceeds its timeout."""


class SessionDisconnectedError(SessionError):
    """Raised when an operation requires a running session."""


class SessionBusyError(SessionError):
    """Raised when a second operation is attempted while one is in flight."""


class SessionProcessError(SessionError):
    """Raised when the emulator process dies or I/O fails unexpectedly."""


class UnexpectedScreenError(SessionError):
    """Raised when a caller expects specific screen content but it is absent."""
