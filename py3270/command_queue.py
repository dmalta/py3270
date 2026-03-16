from __future__ import annotations

from py3270.types import TerminalResponse


class CommandQueue:
    """Serializes one-in-flight commands to s3270. Full implementation in M2."""

    async def enqueue(
        self,
        command: str,
        timeout: int | None = None,
    ) -> TerminalResponse:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError
