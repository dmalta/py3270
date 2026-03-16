from __future__ import annotations

import asyncio

from py3270.types import TerminalResponse


def make_response(data: str = "", ok: bool = True) -> TerminalResponse:
    return TerminalResponse(ok=ok, data=data, status="", raw=[])


class MockSendCommand:
    """Records calls; returns after optional delay; optionally raises."""

    def __init__(self, delay: float = 0.0, raises: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._delay = delay
        self._raises = raises

    async def __call__(self, command: str) -> None:
        self.calls.append(command)
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._raises:
            raise self._raises
