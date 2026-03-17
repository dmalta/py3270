from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class TerminalMode(StrEnum):
    Passthru = "P"
    SuppressExtendedDS = "S"
    NoTN3270E = "N"
    SSLTunnel = "L"
    BindStrict = "B"


class TerminalSetting(StrEnum):
    ConnectionState = "ConnectionState"
    Host = "Host"
    LuName = "LuName"
    Model = "Model"
    Encoding = "Encoding"
    CodePage = "CodePage"
    Aid = "Aid"
    BindPluName = "BindPluName"


class StatusFlag(StrEnum):
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
    Initial = "INITIAL"
    Started = "STARTED"
    Connected = "CONNECTED"
    Disconnected = "DISCONNECTED"
    Stopped = "STOPPED"
    Failed = "FAILED"


@dataclass
class TerminalOptions:
    executable: str = "s3270"
    args: list[str] = field(default_factory=list)
    verbose: bool = False
    timeout: int = 30_000


@dataclass
class TerminalResponse:
    ok: bool
    data: str
    status: str
    raw: list[str]


@dataclass
class ScreenPosition:
    row: int
    col: int


@dataclass
class ScreenSize:
    rows: int
    cols: int


@dataclass
class StatusInfo:
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
    row: int
    col: int
    length: int
    type: Literal["string", "number"]
    trim: bool = True


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
]
