from __future__ import annotations

import logging
import time
from uuid import uuid4

from ibm3270._parser import parse_status, validate_escape_sequences
from ibm3270.transport import Transport
from ibm3270.errors import (
    SessionDisconnectedError,
    SessionProcessError,
    SessionTimeoutError,
)
from ibm3270.types import (
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
    """High-level synchronous wrapper around a single s3270 process.

    Manages the full lifecycle of a terminal session: start, connect, interact,
    disconnect, and stop. All operations are synchronous and blocking.

    Args:
        options: Configuration for the s3270 process. Defaults to `TerminalOptions()`.
        session_id: Stable identifier for this session. Auto-generated if omitted.
    """

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
        """Return `True` if the underlying s3270 process is running."""
        return self._transport.available()

    @property
    def state(self) -> SessionState:
        """Current lifecycle state of the session."""
        return self._state

    @property
    def session_id(self) -> str:
        """Unique identifier for this session."""
        return self._session_id

    def start(self) -> None:
        """Launch the s3270 process. No-op if already running."""
        if self.available():
            return
        self._transport.start(self._options.executable, self._resolved_start_args())
        self._state = SessionState.Started

    def stop(self) -> None:
        """Terminate the s3270 process and release resources."""
        self._transport.stop()
        self._connected = False
        self._state = SessionState.Stopped

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def command(self, cmd: str, *, timeout: int | None = None) -> TerminalResponse:
        """Send a raw s3270 command and return the response.

        Args:
            cmd: The s3270 command string, e.g. `"Enter"` or `"String(text)"`.
            timeout: Milliseconds to wait for a response. Uses the session default if omitted.

        Returns:
            A `TerminalResponse` with `ok`, `data`, and `status`.

        Raises:
            SessionDisconnectedError: If the s3270 process is not running.
            SessionTimeoutError: If the command does not complete within *timeout*.
        """
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
        """Alias for `command`. Sends a single raw s3270 command.

        Args:
            cmd: The s3270 command string.
            timeout: Milliseconds to wait. Uses the session default if omitted.
        """
        return self.command(cmd, timeout=timeout)

    def run_workflow(self, commands: list[str], *, timeout: int | None = None) -> list[TerminalResponse]:
        """Execute a sequence of raw s3270 commands in order.

        Args:
            commands: List of s3270 command strings to execute sequentially.
            timeout: Per-command timeout in milliseconds. Uses the session default if omitted.

        Returns:
            List of `TerminalResponse` objects, one per command.
        """
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
        """Connect to a TN3270 host.

        Args:
            hostname: Hostname or IP address of the mainframe.
            port: TCP port (commonly 23 or 992 for TLS).
            mode: Optional `TerminalMode` prefix (e.g. `NoTN3270E`).
            lu_name: Optional LU name for LU-to-LU connections.

        Returns:
            `TerminalResponse` — `ok` if the connection was established.
        """
        addr = f"{hostname.lower()}:{port}"
        if lu_name:
            addr = f"{lu_name}@{addr}"
        if mode:
            addr = f"{mode.value}:{addr}"
        resp = self.command(f"Connect({addr})")
        self.refresh()
        self._connected = resp.ok
        if self._connected:
            self._state = SessionState.Connected
        return resp

    def disconnect(self) -> TerminalResponse:
        """Disconnect from the host. No-op (returns ok) if not connected."""
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
        """Issue a `Query()` command for the given setting.

        Args:
            setting: The `TerminalSetting` to query (e.g. `Host`, `Model`).

        Returns:
            `TerminalResponse` with the value in `data`.
        """
        return self.command(f"Query({setting.value})")

    def get(self, setting: TerminalSetting) -> str:
        """Return the string value of a terminal setting.

        Args:
            setting: The `TerminalSetting` to retrieve.

        Returns:
            The setting value as a plain string.
        """
        resp = self.query(setting)
        return resp.data

    def cursor(self) -> ScreenPosition | None:
        """Return the current cursor position (1-based row/col), or `None` if unknown."""
        if self._last_status_info is None:
            return None
        s = self._last_status_info
        return self._to_display_position(s.cursor_row, s.cursor_col)

    def screen_size(self) -> ScreenSize | None:
        """Return the current screen dimensions, or `None` if not yet known."""
        if self._last_status_info is None:
            return None
        return ScreenSize(self._last_status_info.rows, self._last_status_info.cols)

    def is_(self, flag: StatusFlag) -> bool:
        """Test a boolean status flag from the last s3270 status line.

        Args:
            flag: A `StatusFlag` such as `Formatted` or `KeyboardLock`.

        Returns:
            `True` if the flag is set.
        """
        val = self._get_status_field(flag)
        if flag == StatusFlag.KeyboardLock:
            return val != "false"
        return val in ("true", "1")

    def current_field(self) -> ScreenPosition | None:
        """Return the position of the current input field (same as `cursor`)."""
        return self.cursor()

    # ------------------------------------------------------------------
    # Screen buffer
    # ------------------------------------------------------------------

    def refresh(self) -> TerminalResponse:
        """Wait for the host and update the internal screen buffer via `Ascii1()`.

        Returns:
            `TerminalResponse` from the `Ascii1()` command.
        """
        self.wait_unlock()
        resp = self.command("Ascii1()")
        self._screen_buffer = resp.data.splitlines()
        return resp

    def screen(self) -> str:
        """Return the last refreshed screen as a single newline-joined string."""
        return "\n".join(self._screen_buffer)

    def get_screen_buffer(self) -> list[str]:
        """Return the last refreshed screen as a list of row strings."""
        return list(self._screen_buffer)

    # ------------------------------------------------------------------
    # Read / write / check
    # ------------------------------------------------------------------

    def read(self, row: int, col: int, length: int, trim: bool = True) -> str:
        """Read a region from the screen buffer.

        Args:
            row: 1-based row number.
            col: 1-based column number.
            length: Number of characters to read.
            trim: Strip trailing whitespace from the result. Defaults to `True`.

        Returns:
            The extracted string, or `""` if the row is out of range.
        """
        if row < 1 or row > len(self._screen_buffer):
            return ""
        line = self._screen_buffer[row - 1]
        result = line[col - 1 : col - 1 + length]
        return result.rstrip() if trim else result

    def line(self, row: int) -> str:
        """Return the full text of a given 1-based row, or `""` if out of range."""
        return self.read(row, 1, len(self._screen_buffer[row - 1]) if 1 <= row <= len(self._screen_buffer) else 0)  
        
    def write(self, text: str, row: int | None = None, col: int | None = None, length: int | None = None) -> TerminalResponse:
        """Move the cursor then type *text* with `String()`.

        Args:
            text: Text to send.
            row: 1-based destination row.
            col: 1-based destination column.
            length: If provided, right-justify *text* in a field of this width.
        """
        if length is not None:
            text = text[:length].ljust(length)
        if row is not None and col is not None:
            self.move(row, col)
        return self.string(text)

    def find(self, text: str, row: int | None = None, col: int | None = None) -> bool:
        """Return `True` if *text* appears at the given screen position, or
        anywhere on the screen if *row* and *col* are omitted.

        Args:
            text: Expected string.
            row: 1-based row. Must be paired with *col*.
            col: 1-based column. Must be paired with *row*.

        Raises:
            ValueError: If only one of *row* / *col* is provided.
        """
        if (row is None) != (col is None):
            raise ValueError("both row and col must be provided, or neither")
        if row is not None:
            return self.read(row, col, len(text)) == text
        return text in self.screen()

    def read_many(self, fields: list[FieldDefinition]) -> FieldDefinitionRecord:
        """Refresh the screen and read multiple fields in one call.

        Args:
            fields: List of `FieldDefinition` descriptors.

        Returns:
            Dict mapping each field's `name` (or `"row,col"` key) to its value.
            Numeric fields are coerced to `float`; blank numeric fields become `None`.
        """
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
        """Send text to the emulator using the `String()` action.

        Args:
            text: The string to type, including s3270 escape sequences.

        Raises:
            ValueError: If *text* contains an invalid s3270 escape sequence.
        """
        validate_escape_sequences(text)
        return self.command(f"String(\"{text}\")")

    def send_text(self, text: str) -> TerminalResponse:
        """Alias for `string`."""
        return self.string(text)

    def enter(self) -> TerminalResponse:
        """Press the Enter key and refresh the screen."""
        response = self.command("Enter")
        self.refresh()
        return response

    def send_enter(self) -> TerminalResponse:
        """Alias for `enter`."""
        return self.enter()

    def tab(self) -> TerminalResponse:
        """Press the Tab key to advance to the next input field."""
        return self.command("Tab")

    def clear(self) -> TerminalResponse:
        """Press the Clear key and refresh the screen. It sends a Clear AID to the host, and waits for the host to unlock the keyboard before returning."""
        response = self.command("Clear")
        self.refresh()
        return response

    def erase_input(self) -> TerminalResponse:
        """Press the Erase Input key, replacing all modifiable fields with NUL characters, and refresh the screen."""
        response = self.command("EraseInput()")
        self.refresh()
        return response

    def pf(self, n: int) -> TerminalResponse:
        """Press a PF function key and refresh the screen.

        Args:
            n: PF key number, 1–24.

        Raises:
            ValueError: If *n* is outside the range 1–24.
        """
        if not 1 <= n <= 24:
            raise ValueError(f"PF key must be 1–24, got {n}")
        response = self.command(f"PF({n})")
        self.refresh()
        return response

    def send_pf(self, n: int) -> TerminalResponse:
        """Alias for `pf`."""
        return self.pf(n)

    def pa(self, n: int) -> TerminalResponse:
        """Press a PA program-attention key and refresh the screen.

        Args:
            n: PA key number, 1–3.

        Raises:
            ValueError: If *n* is outside the range 1–3.
        """
        if not 1 <= n <= 3:
            raise ValueError(f"PA key must be 1–3, got {n}")
        response = self.command(f"PA({n})")
        self.refresh()
        return response

    def move(self, row: int, col: int) -> TerminalResponse:
        """Move the cursor to the specified screen position.

        Args:
            row: 1-based row number.
            col: 1-based column number.
        """
        emulator_row, emulator_col = self._to_emulator_coordinate(row, col)
        return self.command(f"MoveCursor({emulator_row},{emulator_col})")

    def read_screen(self) -> str:
        """Refresh the screen buffer and return its full text content."""
        self.refresh()
        return self.screen()

    # ------------------------------------------------------------------
    # Wait helpers
    # ------------------------------------------------------------------

    def wait(self, timeout: int | None = None) -> TerminalResponse:
        """Issue `Wait()` — blocks until the emulator is ready.

        Args:
            timeout: Milliseconds to wait. Uses the session default if omitted.
        """
        return self.command("Wait()", timeout=timeout)

    def wait_output(self, timeout: int | None = None) -> TerminalResponse:
        """Issue `Wait(Output)` — blocks until the host sends new screen data.

        Args:
            timeout: Milliseconds to wait. Uses the session default if omitted.
        """
        return self.command("Wait(Output)", timeout=timeout)

    def wait_unlock(self, timeout: int | None = None) -> TerminalResponse:
        """Issue `Wait(Unlock)` — blocks until the keyboard is unlocked.

        Args:
            timeout: Milliseconds to wait. Uses the session default if omitted.
        """
        return self.command("Wait(Unlock)", timeout=timeout)

    def wait_ready(self, timeout: int | None = None) -> None:
        """Wait for the keyboard to unlock, then wait for host output.

        Convenience wrapper around `wait_unlock` + `wait_output`.

        Args:
            timeout: Per-call timeout in milliseconds. Uses the session default if omitted.
        """
        self.wait_unlock(timeout)
        self.wait_output(timeout)

    def wait_for(
        self,
        text: str,
        row: int | None = None,
        col: int | None = None,
        timeout: int = 5_000
    ) -> bool:
        """Poll the screen until *text* appears, or *timeout* elapses.

        Args:
            text: The string to watch for.
            row: 1-based row to check. Must be paired with *col*.
            col: 1-based column to check. Must be paired with *row*.
            timeout: Total wait time in milliseconds (capped at 300 000). Defaults to 5 000.

        Returns:
            ``True`` if *text* was found before the deadline or ``False`` if not.

        Raises:
            ValueError: If only one of *row* / *col* is provided.
        """
        if (row is None) != (col is None):
            raise ValueError("both row and col must be provided, or neither")
        timeout = max(0, min(timeout, 300_000))
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            self.refresh()
            if self.find(text, row, col):
                return True
            time.sleep(0.1)

        return False

    def expect(
        self,
        text: str,
        row: int | None = None,
        col: int | None = None,
        timeout: int = 5_000,
        error_message: str = None
    ) -> None:
        """Like `wait_for`, but raises `SessionTimeoutError` if the text is not found."""
        if not self.wait_for(text, row=row, col=col, timeout=timeout):
            if error_message is None:
                error_message = f"Timed out waiting for '{text}' to appear on screen " + \
                    f"(row={row if row is not None else '(any)'}, col={col if col is not None else '(any)'}, timeout={timeout}ms)"
            raise SessionTimeoutError(error_message)