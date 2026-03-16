from __future__ import annotations

from py3270.types import TerminalOptions, TerminalResponse


class Terminal:
    """High-level s3270 wrapper. Full implementation in M4."""

    def __init__(self, options: TerminalOptions | None = None) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def exec(self, command: str) -> TerminalResponse:
        raise NotImplementedError
