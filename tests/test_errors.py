# tests/test_errors.py
from __future__ import annotations

import pytest

from parsedantic.errors import ParseError, get_line_column


def test_get_line_column_single_line() -> None:
    text = "abcdef"
    # Index 0 is first character.
    assert get_line_column(text, 0) == (1, 1)
    # Index 3 is the fourth character.
    assert get_line_column(text, 3) == (1, 4)
    # Index past end is clamped.
    assert get_line_column(text, 10) == (1, 7)


def test_get_line_column_multi_line() -> None:
    text = "one\ntwo\nthree"
    # "t" in "two" is index 4 (0-based).
    assert get_line_column(text, 4) == (2, 1)
    # Last character in "three".
    idx = text.index("three") + len("three") - 1
    assert get_line_column(text, idx) == (3, 5)


def test_get_line_column_empty_text() -> None:
    assert get_line_column("", 0) == (1, 1)
    # Negative index is clamped.
    assert get_line_column("", -5) == (1, 1)


def test_parse_error_str_includes_location_and_context() -> None:
    text = "first line\nsecond line with error\nthird line"
    index = text.index("error") + 1  # somewhere inside the word "error"
    err = ParseError(text=text, index=index, expected="digit")
    message = str(err)

    assert "ParseError" in message
    assert "line 2" in message
    assert "column" in message
    assert "second line with error" in message
    # Marker line should contain a caret.
    assert "^" in message.splitlines()[-1]


@pytest.mark.parametrize(
    "text, index",
    [
        ("", 0),
        ("a", 0),
        ("a", 1),
        ("a\n", 0),
        ("a\n", 1),
        ("a\n", 2),
    ],
)
def test_parse_error_edge_cases_do_not_crash(text: str, index: int) -> None:
    err = ParseError(text=text, index=index, expected="something")
    msg = str(err)
    assert "ParseError" in msg
    assert "^" in msg.splitlines()[-1]
