from __future__ import annotations

import asyncio
from dataclasses import fields

import pytest

import py3270
from py3270 import (
    ConnectionState,
    EmulatorMode,
    FieldDefinition,
    FieldProtection,
    KeyboardState,
    ScreenFormatting,
    ScreenPosition,
    ScreenSize,
    StatusFlag,
    StatusInfo,
    TerminalMode,
    TerminalOptions,
    TerminalResponse,
    TerminalSetting,
)


def test_all_types_importable() -> None:
    assert TerminalOptions.__name__ == "TerminalOptions"
    assert TerminalResponse.__name__ == "TerminalResponse"
    assert ScreenPosition.__name__ == "ScreenPosition"
    assert ScreenSize.__name__ == "ScreenSize"
    assert StatusInfo.__name__ == "StatusInfo"
    assert FieldDefinition.__name__ == "FieldDefinition"


def test_terminal_options_defaults() -> None:
    opts = TerminalOptions()

    assert opts.executable == "s3270"
    assert opts.args == []
    assert opts.verbose is False
    assert opts.timeout == 30_000


def test_terminal_options_custom() -> None:
    opts = TerminalOptions(executable="/usr/local/bin/s3270", timeout=5_000)

    assert opts.executable == "/usr/local/bin/s3270"
    assert opts.timeout == 5_000


@pytest.mark.parametrize("member", ["P", "S", "N", "L", "B"])
def test_terminal_mode_members(member: str) -> None:
    assert TerminalMode(member).value == member


@pytest.mark.parametrize(
    ("enum_cls", "expected"),
    [
        (TerminalSetting, ["ConnectionState", "Host", "LuName", "Model", "Encoding", "CodePage", "Aid", "BindPluName"]),
        (StatusFlag, ["Formatted", "KeyboardLock", "Printer", "Secure", "Tn3270e"]),
        (KeyboardState, ["U", "L", "E"]),
        (ScreenFormatting, ["F", "U"]),
        (FieldProtection, ["P", "U"]),
        (ConnectionState, ["C", "N"]),
        (EmulatorMode, ["I", "L", "C", "P", "N"]),
    ],
)
def test_enum_members(enum_cls: type[object], expected: list[str]) -> None:
    values = [member.value for member in enum_cls]  # type: ignore[attr-defined]

    assert values == expected


def test_keyboard_state_matches_string_value() -> None:
    assert KeyboardState.U == "U"


def test_screen_dataclasses() -> None:
    position = ScreenPosition(row=4, col=9)
    size = ScreenSize(rows=24, cols=80)

    assert position.row == 4
    assert position.col == 9
    assert size.rows == 24
    assert size.cols == 80


def test_terminal_response_instantiation() -> None:
    response = TerminalResponse(ok=True, data="screen", status="status", raw=["screen", "status", "ok"])

    assert response.ok is True
    assert response.data == "screen"
    assert response.status == "status"
    assert response.raw == ["screen", "status", "ok"]


def test_status_info_field_shape() -> None:
    status_fields = [field.name for field in fields(StatusInfo)]

    assert status_fields == [
        "keyboard_state",
        "screen_formatting",
        "field_protection",
        "connection_state",
        "host",
        "emulator_mode",
        "model_number",
        "rows",
        "cols",
        "cursor_row",
        "cursor_col",
        "window_id",
        "command_execution_time",
    ]


def test_status_info_instantiation() -> None:
    status = StatusInfo(
        keyboard_state=KeyboardState.U,
        screen_formatting=ScreenFormatting.F,
        field_protection=FieldProtection.U,
        connection_state=ConnectionState.C,
        host="mvshost",
        emulator_mode=EmulatorMode.C,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=1,
        cursor_col=1,
        window_id="0x0",
        command_execution_time=0.042,
    )

    assert status.rows == 24
    assert status.host == "mvshost"
    assert status.command_execution_time == pytest.approx(0.042)


def test_status_info_null_exec_time() -> None:
    status = StatusInfo(
        keyboard_state=KeyboardState.U,
        screen_formatting=ScreenFormatting.U,
        field_protection=FieldProtection.U,
        connection_state=ConnectionState.N,
        host=None,
        emulator_mode=EmulatorMode.N,
        model_number=2,
        rows=24,
        cols=80,
        cursor_row=0,
        cursor_col=0,
        window_id="0x0",
        command_execution_time=None,
    )

    assert status.command_execution_time is None
    assert status.host is None


def test_field_definition_trim_default() -> None:
    field_definition = FieldDefinition(row=3, col=5, length=10, type="string")

    assert field_definition.trim is True


def test_field_definition_number_type() -> None:
    field_definition = FieldDefinition(row=1, col=1, length=5, type="number", trim=False)

    assert field_definition.type == "number"
    assert field_definition.trim is False


def test_top_level_exports() -> None:
    assert py3270.TerminalMode is TerminalMode
    assert py3270.TerminalOptions is TerminalOptions
    assert py3270.StatusInfo is StatusInfo


def test_version() -> None:
    assert isinstance(py3270.__version__, str)
    assert py3270.__version__.split(".") == ["0", "1", "0"]


async def test_asyncio_smoke() -> None:
    await asyncio.sleep(0)
