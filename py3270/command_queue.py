from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from py3270.types import TerminalResponse


@dataclass
class _QueueEntry:
    command: str
    future: asyncio.Future[TerminalResponse]
    timeout: int  # milliseconds


class CommandQueue:
    """Serializes one-in-flight commands to s3270."""

    def __init__(self, send_command: Callable[[str], Awaitable[None]]) -> None:
        self._send_command = send_command
        self._queue: asyncio.Queue[_QueueEntry] = asyncio.Queue()
        self._current_future: asyncio.Future[TerminalResponse] | None = None
        self._current_command: str | None = None
        self._timeout_handle: asyncio.TimerHandle | None = None
        self._stopped: bool = False
        self._loop_task: asyncio.Task[None] = asyncio.create_task(
            self._process_loop(), name="command-queue-loop"
        )

    async def enqueue(self, command: str, timeout: int) -> TerminalResponse:
        """Add command to queue and wait for its response. Raises RuntimeError if stopped."""
        if self._stopped:
            raise RuntimeError("Queue is stopped")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TerminalResponse] = loop.create_future()
        await self._queue.put(_QueueEntry(command=command, future=future, timeout=timeout))
        return await future

    def handle_response(self, response: TerminalResponse) -> None:
        """Called by Terminal when a complete response is received."""
        if self._current_future is not None and not self._current_future.done():
            if self._timeout_handle is not None:
                self._timeout_handle.cancel()
                self._timeout_handle = None
            self._current_future.set_result(response)
            self._current_future = None

    def handle_error(self, error: Exception) -> None:
        """Called by Terminal when an error response or process error occurs."""
        if self._current_future is not None and not self._current_future.done():
            if self._timeout_handle is not None:
                self._timeout_handle.cancel()
                self._timeout_handle = None
            self._current_future.set_exception(error)
            self._current_future = None

    async def stop(self) -> None:
        """Mark stopped, reject in-flight + pending commands, cancel loop task."""
        if self._stopped:
            return
        self._stopped = True

        # Cancel any pending timeout and reject the in-flight command
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
            self._timeout_handle = None
        if self._current_future is not None and not self._current_future.done():
            self._current_future.set_exception(RuntimeError("Queue stopped"))
            self._current_future = None

        # Drain all pending entries with rejection
        while True:
            try:
                entry = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not entry.future.done():
                entry.future.set_exception(RuntimeError("Process terminated"))

        # Cancel the worker task
        self._loop_task.cancel()
        try:
            await self._loop_task
        except asyncio.CancelledError:
            pass

    def _on_timeout(self) -> None:
        if self._current_future is not None and not self._current_future.done():
            cmd = self._current_command or ""
            self._current_future.set_exception(TimeoutError(f"Command timeout: {cmd}"))
            self._timeout_handle = None
            self._current_future = None

    async def _process_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                entry = await self._queue.get()
            except asyncio.CancelledError:
                break

            if self._stopped:
                if not entry.future.done():
                    entry.future.set_exception(RuntimeError("Process terminated"))
                continue

            self._current_future = entry.future
            self._current_command = entry.command
            self._timeout_handle = loop.call_later(
                entry.timeout / 1000.0, self._on_timeout
            )

            try:
                await self._send_command(entry.command)
            except Exception as exc:
                if self._timeout_handle is not None:
                    self._timeout_handle.cancel()
                    self._timeout_handle = None
                if self._current_future is not None and not self._current_future.done():
                    self._current_future.set_exception(exc)
                self._current_future = None
                self._current_command = None
                continue

            # Wait for handle_response / handle_error / _on_timeout to resolve the future
            try:
                await entry.future
            except Exception:
                pass  # Future was rejected; continue to next command

            if self._current_future is entry.future:
                self._current_future = None
            self._current_command = None
