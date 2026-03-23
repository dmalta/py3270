from __future__ import annotations

from ibm3270.types import TerminalResponse


def make_response(data: str = "", ok: bool = True) -> TerminalResponse:
    return TerminalResponse(ok=ok, data=data, status="", raw=[])


class MockSendCommand:
    """Records calls and can raise an exception."""

    def __init__(self, raises: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._raises = raises

    def __call__(self, command: str) -> None:
        self.calls.append(command)
        if self._raises:
            raise self._raises
