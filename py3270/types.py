from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class TerminalMode(StrEnum):
    P = "P"
    S = "S"
    N = "N"
    L = "L"
    B = "B"


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
    U = "U"
    L = "L"
    E = "E"


class ScreenFormatting(StrEnum):
    F = "F"
    U = "U"


class FieldProtection(StrEnum):
    P = "P"
    U = "U"


class ConnectionState(StrEnum):
    C = "C"
    N = "N"


class EmulatorMode(StrEnum):
    I = "I"  # noqa: E741
    L = "L"
    C = "C"
    P = "P"
    N = "N"


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
    "StatusFlag",
    "StatusInfo",
    "TerminalMode",
    "TerminalOptions",
    "TerminalResponse",
    "TerminalSetting",
]
