import pytest

from py3270._parser import validate_escape_sequences


# ---------------------------------------------------------------------------
# Valid sequences (must NOT raise)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "hello world",           # no escapes
        r"price: \\$10",         # literal backslash via \\
        'say \\"hello\\"',       # escaped double-quote  (Python: say \"hello\")
        r"\b",                   # left arrow (backspace)
        r"\f",                   # clear
        r"\n",                   # enter
        r"\r",                   # newline
        r"\t",                   # tab
        r"\T",                   # BackTab
        r"\e41",                 # EBCDIC 2 hex digits
        r"\eC1D9",               # EBCDIC 4 hex digits
        r"\u41",                 # Unicode 2 hex digits
        r"\u0041",               # Unicode 4 hex digits
        r"\u00041",              # Unicode 5 hex digits
        r"\x41",                 # Unicode \x 2 hex digits
        r"\x0041",               # Unicode \x 4 hex digits
        r"\pa1",                 # PA key 1
        r"\pa2",                 # PA key 2
        r"\pa3",                 # PA key 3
        r"\pf1",                 # PF key 1
        r"\pf9",                 # PF key 9
        r"\pf12",                # PF key 12
        r"\pf24",                # PF key 24
        r"Hello\nWorld",         # escape embedded in plain text
        r"\pf1\pf2",             # two consecutive PF escapes
    ],
)
def test_valid_sequence(text: str) -> None:
    validate_escape_sequences(text)  # must not raise


# ---------------------------------------------------------------------------
# Invalid sequences (MUST raise ValueError)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        r"\z",       # unknown single letter
        r"\c",       # unknown single letter
        r"\1",       # digit after backslash
        r"\e1",      # EBCDIC: only 1 hex digit (need 2 or 4)
        r"\e123",    # EBCDIC: 3 hex digits (need 2 or 4)
        r"\u1",      # Unicode: only 1 hex digit
        r"\x1",      # Unicode \x: only 1 hex digit
        r"\pa0",     # PA key 0 (out of range 1–3)
        r"\pa4",     # PA key 4 (out of range 1–3)
        r"\pf0",     # PF key 0 (out of range 1–24)
        r"\pf25",    # PF key 25 (out of range 1–24)
        r"\p",       # \p with nothing after
        r"\pz",      # \p followed by unknown letter
        "\\",        # lone backslash at end of string
    ],
)
def test_invalid_sequence_raises(text: str) -> None:
    with pytest.raises(ValueError):
        validate_escape_sequences(text)


def test_error_contains_position() -> None:
    with pytest.raises(ValueError, match=r"position \d+"):
        validate_escape_sequences(r"hello \z world")


def test_error_reports_first_occurrence() -> None:
    """When multiple invalid sequences exist, only the first is reported."""
    with pytest.raises(ValueError) as exc_info:
        validate_escape_sequences(r"\z\c")
    assert r"\z" in str(exc_info.value)
