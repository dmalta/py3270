from __future__ import annotations

import logging
import time
from uuid import uuid4

from py3270._parser import parse_status, validate_escape_sequences
from py3270.transport import Transport
from py3270.errors import (
    SessionDisconnectedError,
    SessionProcessError,
)
from py3270.types import (
    EmulatorMode,
    FieldDefinition,
    FieldDefinitionRecord,
    KeyboardState,
    ScreenFormatting,
    ScreenPosition,
    ScreenSize,
    SessionState,
    StatusFlag,
    StatusInfo,
    TerminalMode,
    TerminalOptions,
    TerminalResponse,
    TerminalSetting,
)

_LOG = logging.getLogger(__name__)
_DEFAULT_MODEL = "3279-2"


class Terminal:
    """High-level synchronous s3270 wrapper with sequential session semantics."""

    def __init__(
        self,
        options: TerminalOptions | None = None,
        *,
        session_id: str | None = None,
    ) -> None:
        self._options = options or TerminalOptions()
        self._session_id = session_id or str(uuid4())
        self._transport = Transport(default_timeout_ms=self._options.timeout)
        self._connected: bool = False
        self._screen_buffer: list[str] = []
        self._last_status_info: StatusInfo | None = None
        self._state = SessionState.Initial

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if not self._transport.available():
            self._state = SessionState.Failed
            raise SessionDisconnectedError("Terminal is not running")

    def _get_status_field(self, flag: StatusFlag) -> str:
        if self._last_status_info is None:
            return "false"
        s = self._last_status_info
        if flag == StatusFlag.Formatted:
            return "true" if s.screen_formatting == ScreenFormatting.Formatted else "false"
        if flag == StatusFlag.KeyboardLock:
            return "false" if s.keyboard_state == KeyboardState.Unlocked else "true"
        if flag == StatusFlag.Tn3270e:
            return "true" if s.emulator_mode == EmulatorMode.Mode3270 else "false"
        return "false"

    def _to_emulator_coordinate(self, row: int, col: int) -> tuple[int, int]:
        if row < 1:
            raise ValueError(f"row must be >= 1, got {row}")
        if col < 1:
            raise ValueError(f"col must be >= 1, got {col}")
        return row - 1, col - 1

    def _to_display_position(self, row: int, col: int) -> ScreenPosition:
        return ScreenPosition(row + 1, col + 1)

    def _resolved_start_args(self) -> list[str]:
        args = list(self._options.args)
        if "-model" in args:
            return args
        for index, arg in enumerate(args[:-1]):
            if arg == "-xrm" and "s3270.model:" in args[index + 1]:
                return args
        return ["-model", _DEFAULT_MODEL, *args]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def available(self) -> bool:
        return self._transport.available()

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def session_id(self) -> str:
        return self._session_id

    def start(self) -> None:
        if self.available():
            return
        self._transport.start(self._options.executable, self._resolved_start_args())
        self._state = SessionState.Started

    def stop(self) -> None:
        self._transport.stop()
        self._connected = False
        self._state = SessionState.Stopped

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def command(self, cmd: str, *, timeout: int | None = None) -> TerminalResponse:
        self._assert_running()
        started_at = time.monotonic()
        try:
            response = self._transport.execute(cmd, timeout=timeout)
        except (SessionDisconnectedError, SessionProcessError):
            self._state = SessionState.Failed
            raise

        if response.status:
            self._last_status_info = parse_status(response.status)

        if response.ok:
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            _LOG.debug(
                "session=%s pid=%s cmd=%s elapsed_ms=%d ok=true",
                self._session_id,
                self._transport.pid(),
                cmd,
                elapsed_ms,
            )
        else:
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            _LOG.debug(
                "session=%s pid=%s cmd=%s elapsed_ms=%d ok=false data=%s",
                self._session_id,
                self._transport.pid(),
                cmd,
                elapsed_ms,
                response.data,
            )
        return response

    def run_step(self, cmd: str, *, timeout: int | None = None) -> TerminalResponse:
        return self.command(cmd, timeout=timeout)

    def run_workflow(self, commands: list[str], *, timeout: int | None = None) -> list[TerminalResponse]:
        return [self.command(cmd, timeout=timeout) for cmd in commands]

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def connect(
        self,
        hostname: str,
        port: int,
        *,
        mode: TerminalMode | None = None,
        lu_name: str | None = None,
    ) -> TerminalResponse:
        addr = f"{hostname.lower()}:{port}"
        if lu_name:
            addr = f"{lu_name}@{addr}"
        if mode:
            addr = f"{mode.value}:{addr}"
        resp = self.command(f"Connect({addr})")
        self._connected = resp.ok
        if self._connected:
            self._state = SessionState.Connected
        return resp

    def disconnect(self) -> TerminalResponse:
        if not self._connected:
            return TerminalResponse(ok=True, data="", status="", raw=[])
        resp = self.command("Disconnect")
        self._connected = False
        self._state = SessionState.Disconnected
        return resp

    # ------------------------------------------------------------------
    # Query / status getters
    # ------------------------------------------------------------------

    def query(self, setting: TerminalSetting) -> TerminalResponse:
        return self.command(f"Query({setting.value})")

    def get(self, setting: TerminalSetting) -> str:
        resp = self.query(setting)
        return resp.data

    def cursor(self) -> ScreenPosition | None:
        if self._last_status_info is None:
            return None
        s = self._last_status_info
        return self._to_display_position(s.cursor_row, s.cursor_col)

    def screen_size(self) -> ScreenSize | None:
        if self._last_status_info is None:
            return None
        return ScreenSize(self._last_status_info.rows, self._last_status_info.cols)

    def is_(self, flag: StatusFlag) -> bool:
        val = self._get_status_field(flag)
        if flag == StatusFlag.KeyboardLock:
            return val != "false"
        return val in ("true", "1")

    def current_field(self) -> ScreenPosition | None:
        return self.cursor()

    # ------------------------------------------------------------------
    # Screen buffer
    # ------------------------------------------------------------------

    def refresh(self) -> TerminalResponse:
        resp = self.command("Ascii1()")
        self._screen_buffer = resp.data.splitlines()
        return resp

    def screen(self) -> str:
        return "\n".join(self._screen_buffer)

    def get_screen_buffer(self) -> list[str]:
        return list(self._screen_buffer)

    # ------------------------------------------------------------------
    # Read / write / check
    # ------------------------------------------------------------------

    def read(self, row: int, col: int, length: int, trim: bool = True) -> str:
        if row < 1 or row > len(self._screen_buffer):
            return ""
        line = self._screen_buffer[row - 1]
        result = line[col - 1 : col - 1 + length]
        return result.rstrip() if trim else result

    def write(self, text: str, row: int, col: int, length: int | None = None) -> TerminalResponse:
        if length is not None:
            text = text[:length].rjust(length)
        self.move(row, col)
        return self.string(text)

    def check(self, text: str, row: int, col: int) -> bool:
        return self.read(row, col, len(text)) == text

    def read_many(self, fields: list[FieldDefinition]) -> FieldDefinitionRecord:
        self.refresh()
        result: FieldDefinitionRecord = {}
        for field in fields:
            raw = self.read(field.row, field.col, field.length, trim=field.trim)
            key = field.name or f"{field.row},{field.col}"
            if field.type == "number":
                try:
                    result[key] = float(raw) if raw else None
                except ValueError:
                    result[key] = raw
            else:
                result[key] = raw
        return result

    # ------------------------------------------------------------------
    # Text / input helpers
    # ------------------------------------------------------------------

    def string(self, text: str) -> TerminalResponse:
        validate_escape_sequences(text)
        return self.command(f"String({text})")

    def send_text(self, text: str) -> TerminalResponse:
        return self.string(text)

    def enter(self) -> TerminalResponse:
        return self.command("Enter")

    def send_enter(self) -> TerminalResponse:
        return self.enter()

    def tab(self) -> TerminalResponse:
        return self.command("Tab")

    def clear(self) -> TerminalResponse:
        return self.command("Clear")

    def pf(self, n: int) -> TerminalResponse:
        if not 1 <= n <= 24:
            raise ValueError(f"PF key must be 1–24, got {n}")
        return self.command(f"PF({n})")

    def send_pf(self, n: int) -> TerminalResponse:
        return self.pf(n)

    def pa(self, n: int) -> TerminalResponse:
        if not 1 <= n <= 3:
            raise ValueError(f"PA key must be 1–3, got {n}")
        return self.command(f"PA({n})")

    def move(self, row: int, col: int) -> TerminalResponse:
        emulator_row, emulator_col = self._to_emulator_coordinate(row, col)
        return self.command(f"MoveCursor({emulator_row},{emulator_col})")

    def read_screen(self) -> str:
        self.refresh()
        return self.screen()

    def scrape(self, row: int, col: int, length: int, trim: bool = True) -> str:
        return self.read(row, col, length, trim=trim)

    # ------------------------------------------------------------------
    # Wait helpers
    # ------------------------------------------------------------------

    def wait(self, timeout: int | None = None) -> TerminalResponse:
        return self.command("Wait()", timeout=timeout)

    def wait_output(self, timeout: int | None = None) -> TerminalResponse:
        return self.command("Wait(Output)", timeout=timeout)

    def wait_unlock(self, timeout: int | None = None) -> TerminalResponse:
        return self.command("Wait(Unlock)", timeout=timeout)

    def wait_ready(self, timeout: int | None = None) -> None:
        self.wait_unlock(timeout)
        self.wait_output(timeout)

    def wait_for(
        self,
        text: str,
        row: int | None = None,
        col: int | None = None,
        timeout: int = 30_000,
    ) -> bool:
        if (row is None) != (col is None):
            raise ValueError("both row and col must be provided, or neither")
        timeout = max(0, min(timeout, 300_000))
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            self.refresh()
            if row is not None:
                if self.read(row, col, len(text)) == text:  # type: ignore[arg-type]
                    return True
            else:
                if text in self.screen():
                    return True
            time.sleep(0.1)
        return False
