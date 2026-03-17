from __future__ import annotations

import argparse
from pathlib import Path

from py3270 import StatusFlag, Terminal, TerminalMode, TerminalOptions, TerminalSetting


DEFAULT_HOST = "SUPERSESSION.cpc.ibm.com"
DEFAULT_PORT = 1992
DEFAULT_APPLICATION = "CPPSTSO"
DEFAULT_USERID = "EE"
DEFAULT_EXECUTABLE = str(Path(__file__).with_name("s3270.exe"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a live TN3270 session and walk through the first three screens."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Mainframe hostname")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Mainframe port")
    parser.add_argument(
        "--application",
        default=DEFAULT_APPLICATION,
        help="Application to type on the supersession menu",
    )
    parser.add_argument(
        "--userid",
        default=DEFAULT_USERID,
        help="Dummy user ID to type on the TSO user prompt",
    )
    parser.add_argument(
        "--executable",
        default=DEFAULT_EXECUTABLE,
        help="Path to the s3270 executable",
    )
    parser.add_argument(
        "--model",
        help="Optional s3270 terminal model override, e.g. 3279-2 for 24x80",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20_000,
        help="Default command timeout in milliseconds",
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Disable SSL/TLS connection mode",
    )
    return parser.parse_args()


def print_response(label: str, response_ok: bool, details: str = "") -> None:
    status = "ok" if response_ok else "error"
    print(f"[{label}] {status}")
    if details:
        print(details)


def to_display_cursor(term: Terminal) -> str:
    cursor = term.cursor()
    if cursor is None:
        return "unknown"
    return f"({cursor.row},{cursor.col})"


def find_input_row_and_col(term: Terminal) -> tuple[int, int]:
    buffer = term.get_screen_buffer()
    for row_index in range(len(buffer) - 1, -1, -1):
        line = buffer[row_index]
        prompt_index = line.find(">")
        if prompt_index != -1:
            return row_index + 1, prompt_index + 3
    raise RuntimeError("Could not locate the application input prompt on screen 1")


def refresh_and_dump(term: Terminal, label: str) -> None:
    term.refresh()
    screen_size = term.screen_size()

    print(f"\n=== {label} ===")
    print(f"state: {term.state}")
    print(f"available: {term.available()}")
    print(f"host query: {term.get(TerminalSetting.Host)!r}")
    print(f"model query: {term.get(TerminalSetting.Model)!r}")
    print(f"connection query: {term.get(TerminalSetting.ConnectionState)!r}")
    print(f"screen size: {screen_size}")
    print(f"cursor: {to_display_cursor(term)}")
    print(f"formatted: {term.is_(StatusFlag.Formatted)}")
    print(f"keyboard locked: {term.is_(StatusFlag.KeyboardLock)}")
    print(f"tn3270e mode: {term.is_(StatusFlag.Tn3270e)}")
    print("\n--- screen ---")
    print(term.screen())


def require_text(term: Terminal, text: str, timeout: int, label: str) -> None:
    if not term.wait_for(text, timeout=timeout):
        term.refresh()
        raise RuntimeError(f"Did not reach {label!r}. Current screen:\n{term.screen()}")


def require_ok(label: str, response_data: str, response_ok: bool, response_status: str) -> None:
    print_response(label, response_ok, response_data or response_status)
    if not response_ok:
        raise RuntimeError(f"{label} failed: {response_data or response_status}")


def main() -> int:
    args = parse_args()
    mode = None if args.no_tls else TerminalMode.SSLTunnel
    terminal_args: list[str] = []
    if args.model:
        terminal_args.extend(["-model", args.model])

    term = Terminal(
        TerminalOptions(
            executable=args.executable,
            args=terminal_args,
            timeout=args.timeout,
        )
    )
    try:
        term.start()
        print(f"Using executable: {args.executable}")
        print(f"Requested model override: {args.model or 'none (Terminal default applies)'}")
        print(f"Connecting to {args.host}:{args.port} with tls={not args.no_tls}")

        connect_response = term.connect(args.host, args.port, mode=mode)
        print_response("connect", connect_response.ok, connect_response.data)
        if not connect_response.ok:
            raise RuntimeError(f"Connection failed: {connect_response.data or connect_response.status}")

        require_text(term, "Enter application or EXIT to logoff.", args.timeout, "screen 1")
        refresh_and_dump(term, "Screen 1: CL-Supersession")

        print("\nDiagnostics on screen 1:")
        input_row, input_col = find_input_row_and_col(term)
        print(f"application prompt row: {term.read(input_row - 1, 1, 80, trim=False)!r}")
        print(f"application input row: {term.read(input_row, 1, 20, trim=False)!r}")
        print(f"command prompt found: {term.check('>', input_row, input_col - 2)}")

        print(f"\nNavigating to application {args.application!r} using move() + string() + enter()")
        cursor = term.cursor()
        if cursor is not None:
            move_response = term.move(cursor.row, cursor.col)
            require_ok("move", move_response.data, move_response.ok, move_response.status)
        string_response = term.string(args.application)
        require_ok("string", string_response.data, string_response.ok, string_response.status)
        enter_response = term.enter()
        require_ok("enter", enter_response.data, enter_response.ok, enter_response.status)

        require_text(term, "IKJ56700A ENTER USERID -", args.timeout, "screen 2")
        refresh_and_dump(term, "Screen 2: TSO user prompt")

        print(f"\nSubmitting dummy user ID {args.userid!r} using string() + enter()")
        print(f"screen 2 cursor before typing: {to_display_cursor(term)}")
        string_response = term.string(args.userid)
        require_ok(
            "userid string",
            string_response.data,
            string_response.ok,
            string_response.status,
        )
        enter_response = term.enter()
        require_ok(
            "userid enter",
            enter_response.data,
            enter_response.ok,
            enter_response.status,
        )

        require_text(term, "TSO/E LOGON", args.timeout, "screen 3")
        refresh_and_dump(term, "Screen 3: TSO/E LOGON")

        print("\nReached the expected stop point on screen 3.")
        return 0
    finally:
        try:
            if term.available():
                term.disconnect()
        finally:
            term.stop()


if __name__ == "__main__":
    raise SystemExit(main())
