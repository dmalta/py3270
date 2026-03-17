from __future__ import annotations

import re
from typing import Callable

from py3270.types import (
    ConnectionState,
    EmulatorMode,
    FieldProtection,
    KeyboardState,
    ScreenFormatting,
    StatusInfo,
    TerminalResponse,
)


class _ResponseParser:
    """Stateful parser that buffers s3270 stdout chunks and emits complete
    :class:`~py3270.types.TerminalResponse` objects via a callback."""

    def __init__(self, on_complete: Callable[[TerminalResponse], None]) -> None:
        self._on_complete = on_complete
        self._buffer: str = ""
        self._lines: list[str] = []

    def feed(self, chunk: str) -> None:
        """Append *chunk* to the internal buffer and emit any complete responses."""
        self._buffer += chunk
        while True:
            newline_pos = self._buffer.find("\n")
            if newline_pos == -1:
                break
            line = self._buffer[:newline_pos].rstrip("\r")
            self._buffer = self._buffer[newline_pos + 1 :]

            if line == "ok" or line.startswith("error"):
                self._emit(line)
            else:
                self._lines.append(line)

    def _emit(self, terminal_line: str) -> None:
        accumulated = self._lines
        self._lines = []

        if not accumulated:
            status = ""
            data_lines: list[str] = []
        else:
            status = accumulated[-1]
            data_lines = accumulated[:-1]

        stripped = [dl[6:] if dl.startswith("data: ") else dl for dl in data_lines]
        data = "\n".join(stripped)
        raw = accumulated + [terminal_line]

        self._on_complete(
            TerminalResponse(
                ok=(terminal_line == "ok"),
                data=data,
                status=status,
                raw=raw,
            )
        )


# ---------------------------------------------------------------------------
# Status-line parser
# ---------------------------------------------------------------------------


def parse_status(line: str) -> StatusInfo | None:
    """Parse an s3270 status line and return a :class:`~py3270.types.StatusInfo`.

    Returns ``None`` for empty, short, or structurally invalid lines so callers
    can safely skip without crashing.
    """
    if not line:
        return None
    parts = line.split()
    if len(parts) < 12:
        return None

    try:
        conn_raw = parts[3]
        if conn_raw.startswith("C(") and conn_raw.endswith(")"):
            conn_state = ConnectionState.Connected
            host: str | None = conn_raw[2:-1]
        elif conn_raw == "N":
            conn_state = ConnectionState.NotConnected
            host = None
        else:
            return None

        exec_time = None if parts[11] == "-" else float(parts[11])

        return StatusInfo(
            keyboard_state=KeyboardState(parts[0]),
            screen_formatting=ScreenFormatting(parts[1]),
            field_protection=FieldProtection(parts[2]),
            connection_state=conn_state,
            host=host,
            emulator_mode=EmulatorMode(parts[4]),
            model_number=int(parts[5]),
            rows=int(parts[6]),
            cols=int(parts[7]),
            cursor_row=int(parts[8]),
            cursor_col=int(parts[9]),
            window_id=parts[10],
            command_execution_time=exec_time,
        )
    except (ValueError, IndexError, KeyError):
        return None


# ---------------------------------------------------------------------------
# Escape-sequence validator
# ---------------------------------------------------------------------------

_HEX = re.compile(r"[0-9a-fA-F]+")
_PF = re.compile(r"(1\d|2[0-4]|[1-9])(?!\d)")
_PA = re.compile(r"[1-3](?!\d)")


def validate_escape_sequences(text: str) -> None:
    """Scan *text* for s3270 escape sequences and raise :exc:`ValueError` on
    the first invalid one.

    Valid sequences mirror Appendix B of the s3270 documentation:
    ``\\\\``, ``\\"``, ``\\b``, ``\\f``, ``\\n``, ``\\r``, ``\\t``, ``\\T``,
    ``\\eXX`` / ``\\eXXXX`` (EBCDIC), ``\\uXX``–``\\uXXXXX`` (Unicode),
    ``\\xXX``–``\\xXXXXX`` (Unicode), ``\\pa1``–``\\pa3``, ``\\pf1``–``\\pf24``.
    """
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "\\":
            i += 1
            continue

        # We have a backslash at position i.
        if i + 1 >= n:
            raise ValueError(f"Incomplete escape sequence at position {i}: {repr(text[i:])}")

        next_char = text[i + 1]

        if next_char in ("\\", '"', "b", "f", "n", "r", "t", "T"):
            i += 2

        elif next_char == "e":
            # \eXX or \eXXXX — exactly 2 or 4 hex digits
            m = _HEX.match(text, i + 2)
            hex_len = (m.end() - (i + 2)) if m else 0
            # Clamp to at most 4 (greedy match might give more)
            hex_len = min(hex_len, 4)
            if hex_len not in (2, 4):
                raise ValueError(f"Invalid EBCDIC escape at position {i}: {repr(text[i : i + 6])}")
            i += 2 + hex_len

        elif next_char in ("u", "x"):
            # \uXX to \uXXXXX / \xXX to \xXXXXX — 2 to 5 hex digits
            m = _HEX.match(text, i + 2)
            hex_len = (m.end() - (i + 2)) if m else 0
            # Clamp to at most 5
            hex_len = min(hex_len, 5)
            if hex_len < 2:
                raise ValueError(f"Invalid Unicode escape at position {i}: {repr(text[i : i + 7])}")
            i += 2 + hex_len

        elif next_char == "p":
            if i + 2 >= n:
                raise ValueError(f"Incomplete \\p escape at position {i}: {repr(text[i:])}")
            key_type = text[i + 2]
            if key_type == "a":
                m = _PA.match(text, i + 3)
                if not m:
                    raise ValueError(f"Invalid PA key at position {i}: {repr(text[i : i + 5])}")
                i += 3 + (m.end() - (i + 3))
            elif key_type == "f":
                m = _PF.match(text, i + 3)
                if not m:
                    raise ValueError(f"Invalid PF key at position {i}: {repr(text[i : i + 6])}")
                i += 3 + (m.end() - (i + 3))
            else:
                raise ValueError(f"Invalid \\p escape at position {i}: {repr(text[i : i + 4])}")

        else:
            raise ValueError(f"Invalid escape sequence at position {i}: {repr(text[i : i + 2])}")
