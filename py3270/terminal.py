from __future__ import annotations

import asyncio
from typing import Any

from py3270._parser import _ResponseParser, parse_status, validate_escape_sequences
from py3270.command_queue import CommandQueue
from py3270.types import (
    EmulatorMode,
    FieldDefinition,
    FieldDefinitionRecord,
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


class Terminal:
    """High-level s3270 wrapper — manages the s3270 subprocess lifecycle and exposes
    the full API: commands, connectivity, screen operations, and wait helpers."""

    def __init__(self, options: TerminalOptions | None = None) -> None:
        self._options = options or TerminalOptions()
        self._process: asyncio.subprocess.Process | None = None
        self._connected: bool = False
        self._screen_buffer: list[str] = []
        self._last_status_info: StatusInfo | None = None
        self._read_loop_task: asyncio.Task[None] | None = None
        # _parser and _command_queue are created lazily in start() so that
        # Terminal() can be instantiated in a synchronous context.
        self._parser: _ResponseParser | None = None
        self._command_queue: CommandQueue | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self._process is None:
            raise RuntimeError("Terminal is not running")

    async def _send_raw(self, command: str) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Terminal is not running")
        self._process.stdin.write((command + "\n").encode())
        await self._process.stdin.drain()

    async def _read_loop(self) -> None:
        assert self._process is not None
        assert self._process.stdout is not None
        assert self._parser is not None
        while True:
            chunk = await self._process.stdout.read(4096)
            if not chunk:
                break
            self._parser.feed(chunk.decode(errors="replace"))
        # Process ended — drain the command queue
        if self._command_queue is not None:
            await self._command_queue.stop()

    def _on_response(self, response: TerminalResponse) -> None:
        if self._command_queue is None:
            return
        if response.status:
            self._last_status_info = parse_status(response.status)
        if response.ok:
            self._command_queue.handle_response(response)
        else:
            self._command_queue.handle_error(
                RuntimeError(f"s3270 error: {response.data}")
            )

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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def available(self) -> bool:
        return self._process is not None

    async def start(self) -> None:
        if self._process is not None:
            return
        # Create fresh parser and command queue for this session.
        self._parser = _ResponseParser(on_complete=self._on_response)
        self._command_queue = CommandQueue(send_command=self._send_raw)
        cmd = [self._options.executable, "-script"] + self._options.args
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._read_loop_task = asyncio.create_task(
            self._read_loop(), name="s3270-reader"
        )

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._command_queue is not None:
            await self._command_queue.stop()
        if self._read_loop_task:
            self._read_loop_task.cancel()
            try:
                await self._read_loop_task
            except asyncio.CancelledError:  # NOSONAR
                pass
        try:
            self._process.stdin.close()
            self._process.terminate()
            await self._process.wait()
        except Exception:
            pass
        self._process = None
        self._connected = False

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    async def command(self, cmd: str, *, timeout: int | None = None) -> TerminalResponse:
        self._assert_running()
        assert self._command_queue is not None
        t_sec = (timeout if timeout is not None else self._options.timeout) / 1000
        async with asyncio.timeout(t_sec):
            return await self._command_queue.enqueue(cmd)

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    async def connect(
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
        resp = await self.command(f"Connect({addr})")
        self._connected = resp.ok
        return resp

    async def disconnect(self) -> TerminalResponse:
        if not self._connected:
            return TerminalResponse(ok=True, data="", status="", raw=[])
        resp = await self.command("Disconnect")
        self._connected = False
        return resp

    # ------------------------------------------------------------------
    # Query / status getters
    # ------------------------------------------------------------------

    async def query(self, setting: TerminalSetting) -> TerminalResponse:
        return await self.command(f"Query({setting.value})")

    async def get(self, setting: TerminalSetting) -> str:
        resp = await self.query(setting)
        return resp.data

    def cursor(self) -> ScreenPosition | None:
        if self._last_status_info is None:
            return None
        s = self._last_status_info
        return ScreenPosition(s.cursor_row, s.cursor_col)

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

    async def refresh(self) -> TerminalResponse:
        resp = await self.command("Ascii1()")
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

    async def write(
        self, text: str, row: int, col: int, length: int | None = None
    ) -> TerminalResponse:
        if length is not None:
            text = text[:length].ljust(length)
        await self.command(f"MoveCursor({row},{col})")
        return await self.string(text)

    def check(self, text: str, row: int, col: int) -> bool:
        return self.read(row, col, len(text)) == text

    async def read_many(self, fields: list[FieldDefinition]) -> FieldDefinitionRecord:
        await self.refresh()
        result: FieldDefinitionRecord = {}
        for field in fields:
            raw = self.read(field.row, field.col, field.length, trim=field.trim)
            if field.type == "number":
                try:
                    result[f"{field.row},{field.col}"] = float(raw) if raw else None
                except ValueError:
                    result[f"{field.row},{field.col}"] = None
            else:
                result[f"{field.row},{field.col}"] = raw
        return result

    # ------------------------------------------------------------------
    # Text / input helpers
    # ------------------------------------------------------------------

    async def string(self, text: str) -> TerminalResponse:
        validate_escape_sequences(text)
        return await self.command(f"String({text})")

    async def enter(self) -> TerminalResponse:
        return await self.command("Enter")

    async def tab(self) -> TerminalResponse:
        return await self.command("Tab")

    async def clear(self) -> TerminalResponse:
        return await self.command("Clear")

    async def pf(self, n: int) -> TerminalResponse:
        if not 1 <= n <= 24:
            raise ValueError(f"PF key must be 1–24, got {n}")
        return await self.command(f"PF({n})")

    async def pa(self, n: int) -> TerminalResponse:
        if not 1 <= n <= 3:
            raise ValueError(f"PA key must be 1–3, got {n}")
        return await self.command(f"PA({n})")

    async def move(self, row: int, col: int) -> TerminalResponse:
        return await self.command(f"MoveCursor({row},{col})")

    # ------------------------------------------------------------------
    # Wait helpers
    # ------------------------------------------------------------------

    async def wait(self, timeout: int | None = None) -> TerminalResponse:
        return await self.command("Wait()", timeout=timeout)

    async def wait_output(self, timeout: int | None = None) -> TerminalResponse:
        return await self.command("Wait(Output)", timeout=timeout)

    async def wait_unlock(self, timeout: int | None = None) -> TerminalResponse:
        return await self.command("Wait(Unlock)", timeout=timeout)

    async def wait_ready(self, timeout: int | None = None) -> None:
        await self.wait_unlock(timeout)
        await self.wait_output(timeout)

    async def wait_for(
        self,
        text: str,
        row: int | None = None,
        col: int | None = None,
        timeout: int = 30_000,
    ) -> bool:
        if (row is None) != (col is None):
            raise ValueError("both row and col must be provided, or neither")
        timeout = max(0, min(timeout, 300_000))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout / 1000
        while loop.time() < deadline:
            await self.refresh()
            if row is not None:
                if self.read(row, col, len(text)) == text:  # type: ignore[arg-type]
                    return True
            else:
                if text in self.screen():
                    return True
            await asyncio.sleep(0.1)
        return False


def run_sync(coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute an async callable synchronously.

    Raises ``RuntimeError`` when called from within a running event loop; in
    that case use ``await`` instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            "run_sync() cannot be called from within a running event loop. "
            "Use 'await' instead, or call from a non-async context."
        )
    return asyncio.run(coro_fn(*args, **kwargs))
