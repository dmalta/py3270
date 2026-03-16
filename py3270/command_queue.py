from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from py3270.types import TerminalResponse


@dataclass
class _QueueEntry:
    command: str
    future: asyncio.Future[TerminalResponse]


class CommandQueue:
    """Serializes one-in-flight commands to s3270."""

    def __init__(self, send_command: Callable[[str], Awaitable[None]]) -> None:
        self._send_command = send_command
        self._queue: asyncio.Queue[_QueueEntry] = asyncio.Queue()
        self._current_future: asyncio.Future[TerminalResponse] | None = None
        self._current_command: str | None = None
        self._stopped: bool = False
        self._loop_task: asyncio.Task[None] = asyncio.create_task(
            self._process_loop(), name="command-queue-loop"
        )

    async def enqueue(self, command: str) -> TerminalResponse:
        """Add command to queue and wait for its response. Raises RuntimeError if stopped."""
        if self._stopped:
            raise RuntimeError("Queue is stopped")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TerminalResponse] = loop.create_future()
        await self._queue.put(_QueueEntry(command=command, future=future))
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:  # NOSONAR
            # Intentional: converts caller's asyncio.timeout() CancelledError into a
            # descriptive TimeoutError; asyncio.Timeout.__aexit__ still calls uncancel().
            error = TimeoutError(f"Command timeout: {command}")
            if not future.done():
                future.set_exception(error)
            raise error from None

    def handle_response(self, response: TerminalResponse) -> None:
        """Called by Terminal when a complete response is received."""
        if self._current_future is not None and not self._current_future.done():
            self._current_future.set_result(response)
            self._current_future = None

    def handle_error(self, error: Exception) -> None:
        """Called by Terminal when an error response or process error occurs."""
        if self._current_future is not None and not self._current_future.done():
            self._current_future.set_exception(error)
            self._current_future = None

    async def stop(self) -> None:
        """Mark stopped, reject in-flight + pending commands, cancel loop task."""
        if self._stopped:
            return
        self._stopped = True

        # Reject the in-flight command
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

        # Cancel the worker task; gather absorbs the resulting CancelledError
        self._loop_task.cancel()
        await asyncio.gather(self._loop_task, return_exceptions=True)

    async def _dispatch_entry(self, entry: _QueueEntry) -> None:
        """Execute one queue entry: send the command then wait for its future to resolve."""
        self._current_future = entry.future
        self._current_command = entry.command
        try:
            await self._send_command(entry.command)
        except Exception as exc:
            if not entry.future.done():
                entry.future.set_exception(exc)
            self._current_future = None
            self._current_command = None
            return
        try:
            await entry.future
        except Exception:
            pass  # Future was rejected (timeout, stop, error); advance to next command
        if self._current_future is entry.future:
            self._current_future = None
        self._current_command = None

    async def _process_loop(self) -> None:
        while True:
            entry = await self._queue.get()
            if self._stopped:
                if not entry.future.done():
                    entry.future.set_exception(RuntimeError("Process terminated"))
                continue
            await self._dispatch_entry(entry)
