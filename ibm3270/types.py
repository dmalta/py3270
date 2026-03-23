from __future__ import annotations

__docformat__ = "google"

from dataclasses import dataclass, field as dataclass_field
from enum import StrEnum
from typing import Literal


class TerminalMode(StrEnum):
    """Connection mode prefix passed to `Connect()`."""

    Passthru = "P"
    SuppressExtendedDS = "S"
    NoTN3270E = "N"
    SSLTunnel = "L"
    BindStrict = "B"


class TerminalSetting(StrEnum):
    """Keys accepted by the s3270 `Query()` action."""

    ConnectionState = "ConnectionState"
    Host = "Host"
    LuName = "LuName"
    Model = "Model"
    Encoding = "Encoding"
    CodePage = "CodePage"
    Aid = "Aid"
    BindPluName = "BindPluName"


class StatusFlag(StrEnum):
    """Boolean status fields readable via `Terminal.is_`."""

    Formatted = "Formatted"
    KeyboardLock = "KeyboardLock"
    Printer = "Printer"
    Secure = "Secure"
    Tn3270e = "Tn3270e"


class KeyboardState(StrEnum):
    Unlocked = "U"
    Locked = "L"
    Error = "E"


class ScreenFormatting(StrEnum):
    Formatted = "F"
    Unformatted = "U"


class FieldProtection(StrEnum):
    Protected = "P"
    Unprotected = "U"


class ConnectionState(StrEnum):
    Connected = "C"
    NotConnected = "N"


class EmulatorMode(StrEnum):
    Mode3270 = "I"
    NVTLine = "L"
    NVTCharacter = "C"
    Unnegotiated = "P"
    NotConnected = "N"


class SessionState(StrEnum):
    """Lifecycle state of a `Terminal` session."""

    Initial = "INITIAL"
    Started = "STARTED"
    Connected = "CONNECTED"
    Disconnected = "DISCONNECTED"
    Stopped = "STOPPED"
    Failed = "FAILED"


@dataclass
class TerminalOptions:
    """Configuration for launching an s3270 process.

    Attributes:
        executable: Path or name of the s3270 binary. Defaults to `"s3270"`.
        args: Extra command-line arguments forwarded to s3270.
        verbose: Reserved for future debug-logging use.
        timeout: Default command timeout in milliseconds. Defaults to `30_000`.
    """

    executable: str = "s3270"
    args: list[str] = dataclass_field(default_factory=list)
    verbose: bool = False
    timeout: int = 30_000


@dataclass
class TerminalResponse:
    """Result of a single s3270 command.

    Attributes:
        ok: `True` if s3270 responded with `ok`.
        data: Payload text (lines after `data: ` prefix are stripped).
        status: The raw s3270 status line, if present.
        raw: All lines received from s3270 for this command.
    """

    ok: bool
    data: str
    status: str
    raw: list[str]


@dataclass
class ScreenPosition:
    """1-based (row, col) coordinate on the terminal screen."""

    row: int
    col: int


@dataclass
class ScreenSize:
    """Terminal screen dimensions in rows and columns."""

    rows: int
    cols: int


@dataclass
class StatusInfo:
    """Parsed s3270 status line, updated after each successful command.

    Attributes:
        keyboard_state: Whether the keyboard is unlocked, locked, or in error.
        screen_formatting: Formatted or unformatted screen.
        field_protection: Protection state of the current field.
        connection_state: Connected or not connected.
        host: Hostname from the status line, or `None` if not connected.
        emulator_mode: Current emulator negotiation mode.
        model_number: Active 3270 model number.
        rows: Screen height in rows.
        cols: Screen width in columns.
        cursor_row: 0-based cursor row from s3270.
        cursor_col: 0-based cursor column from s3270.
        window_id: X11 window ID or `"0"` on non-X platforms.
        command_execution_time: Last command latency in seconds, or `None`.
    """
    keyboard_state: KeyboardState
    screen_formatting: ScreenFormatting
    field_protection: FieldProtection
    connection_state: ConnectionState
    host: str | None
    emulator_mode: EmulatorMode
    model_number: int
    rows: int
    cols: int
    cursor_row: int
    cursor_col: int
    window_id: str
    command_execution_time: float | None


@dataclass
class FieldDefinition:
    """Descriptor for a single screen field used with `Terminal.read_many`.

    Attributes:
        row: 1-based row.
        col: 1-based column.
        length: Number of characters to read.
        type: `"string"` (default) or `"number"` for float coercion.
        trim: Strip trailing whitespace. Defaults to `True`.
        name: Optional key in the result dict. Defaults to `"row,col"`.
    """

    row: int
    col: int
    length: int
    type: Literal["string", "number"] = "string"
    trim: bool = True
    name: str | None = None


def field(
    row: int,
    col: int,
    length: int,
    type: Literal["string", "number"] = "string",
    *,
    trim: bool = True,
    name: str | None = None,
) -> FieldDefinition:
    """Convenience constructor for `FieldDefinition`.

    Args:
        row: 1-based row.
        col: 1-based column.
        length: Number of characters to read.
        type: `"string"` or `"number"`.
        trim: Strip trailing whitespace. Defaults to `True`.
        name: Optional key in the result dict.

    Returns:
        A `FieldDefinition` instance.
    """
    return FieldDefinition(
        row=row,
        col=col,
        length=length,
        type=type,
        trim=trim,
        name=name,
    )


FieldDefinitionRecord = dict[str, str | float | None]

__all__ = [
    "ConnectionState",
    "EmulatorMode",
    "FieldDefinition",
    "FieldDefinitionRecord",
    "FieldProtection",
    "KeyboardState",
    "ScreenFormatting",
    "ScreenPosition",
    "ScreenSize",
    "SessionState",
    "StatusFlag",
    "StatusInfo",
    "TerminalMode",
    "TerminalOptions",
    "TerminalResponse",
    "TerminalSetting",
    "field",
]
