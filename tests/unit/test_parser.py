import pytest

from py3270._parser import _ResponseParser, parse_status
from py3270.types import ConnectionState, KeyboardState, TerminalResponse


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def collect_responses(chunks: list[str]) -> list[TerminalResponse]:
    results: list[TerminalResponse] = []
    parser = _ResponseParser(on_complete=results.append)
    for chunk in chunks:
        parser.feed(chunk)
    return results


# ---------------------------------------------------------------------------
# T2: Response framing tests
# ---------------------------------------------------------------------------


def test_single_chunk_ok() -> None:
    responses = collect_responses(["U F U N I 2 24 80 0 0 0x0 -\nok\n"])
    assert len(responses) == 1
    assert responses[0].ok is True
    assert responses[0].data == ""


def test_single_chunk_with_data() -> None:
    chunk = "data: HELLO WORLD                  \nU F U C(mvshost:23) I 2 24 80 5 10 0x0 0.042\nok\n"
    responses = collect_responses([chunk])
    assert len(responses) == 1
    assert responses[0].ok is True
    assert responses[0].data == "HELLO WORLD                  "
    assert "mvshost" in responses[0].status


def test_error_response() -> None:
    responses = collect_responses(["error: not connected\n"])
    assert len(responses) == 1
    assert responses[0].ok is False


def test_data_prefix_stripped() -> None:
    responses = collect_responses(["data: some content\nU F U N I 2 24 80 0 0 0x0 -\nok\n"])
    assert responses[0].data == "some content"


def test_chunked_split_mid_line() -> None:
    chunks = ["data: scr", "een content\nU F U N I 2 24 80 0 0 0x0 -\nok\n"]
    responses = collect_responses(chunks)
    assert len(responses) == 1
    assert responses[0].data == "screen content"


def test_chunked_split_at_newline() -> None:
    chunks = ["data: line1\n", "U F U N I 2 24 80 0 0 0x0 -\n", "ok\n"]
    responses = collect_responses(chunks)
    assert len(responses) == 1


def test_chunked_split_inside_ok() -> None:
    chunks = ["U F U N I 2 24 80 0 0 0x0 -\no", "k\n"]
    responses = collect_responses(chunks)
    assert len(responses) == 1
    assert responses[0].ok is True


def test_two_responses_in_one_chunk() -> None:
    chunk = "U F U N I 2 24 80 0 0 0x0 -\nok\nU F U N I 2 24 80 0 0 0x0 -\nok\n"
    responses = collect_responses([chunk])
    assert len(responses) == 2


def test_empty_chunk_is_noop() -> None:
    responses = collect_responses([""])
    assert responses == []


def test_response_with_no_data_lines() -> None:
    chunk = "U F U N I 2 24 80 0 0 0x0 -\nok\n"
    responses = collect_responses([chunk])
    assert responses[0].data == ""


def test_crlf_line_endings() -> None:
    chunk = "U F U N I 2 24 80 0 0 0x0 -\r\nok\r\n"
    responses = collect_responses([chunk])
    assert len(responses) == 1
    assert responses[0].ok is True


def test_raw_field_includes_all_lines() -> None:
    chunk = "data: abc\nU F U N I 2 24 80 0 0 0x0 -\nok\n"
    responses = collect_responses([chunk])
    assert "ok" in responses[0].raw


# ---------------------------------------------------------------------------
# T4: Status-line parser tests
# ---------------------------------------------------------------------------

VALID_STATUS = "U F U C(mvshost:23) I 2 24 80 5 10 0x0 0.042"
DISCONNECTED_STATUS = "U U U N N 2 24 80 0 0 0x0 -"


def test_parse_status_connected() -> None:
    s = parse_status(VALID_STATUS)
    assert s is not None
    assert s.connection_state == ConnectionState.Connected
    assert s.host == "mvshost:23"
    assert s.rows == 24
    assert s.cols == 80
    assert s.cursor_row == 5
    assert s.cursor_col == 10
    assert s.model_number == 2
    assert s.command_execution_time == pytest.approx(0.042)


def test_parse_status_disconnected() -> None:
    s = parse_status(DISCONNECTED_STATUS)
    assert s is not None
    assert s.connection_state == ConnectionState.NotConnected
    assert s.host is None
    assert s.command_execution_time is None


def test_parse_status_empty_returns_none() -> None:
    assert parse_status("") is None


def test_parse_status_too_few_fields_returns_none() -> None:
    assert parse_status("U F U N I 2 24") is None


def test_parse_status_exec_time_dash_is_none() -> None:
    s = parse_status(DISCONNECTED_STATUS)
    assert s is not None
    assert s.command_execution_time is None


def test_parse_status_exec_time_float() -> None:
    s = parse_status(VALID_STATUS)
    assert s is not None
    assert isinstance(s.command_execution_time, float)


@pytest.mark.parametrize(
    "raw,expected_kb",
    [
        ("U F U N I 2 24 80 0 0 0x0 -", "U"),
        ("L F U N I 2 24 80 0 0 0x0 -", "L"),
        ("E F U N I 2 24 80 0 0 0x0 -", "E"),
    ],
)
def test_keyboard_state_variants(raw: str, expected_kb: str) -> None:
    s = parse_status(raw)
    assert s is not None
    assert s.keyboard_state == KeyboardState(expected_kb)


def test_parse_status_invalid_enum_returns_none() -> None:
    # 'Z' is not a valid KeyboardState
    assert parse_status("Z F U N I 2 24 80 0 0 0x0 -") is None
