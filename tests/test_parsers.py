# tests/test_parsers.py
from __future__ import annotations

import re

import pytest
from parsy import ParseError as ParsyError, Parser

from parsedantic.parsers import (
    any_char,
    float_num,
    integer,
    literal,
    pattern,
    whitespace,
    word,
)


def test_literal_matches_exact_text() -> None:
    parser = literal("hello")
    assert isinstance(parser, Parser)
    assert parser.parse("hello") == "hello"

    with pytest.raises(ParsyError):
        parser.parse("hello world")

    with pytest.raises(ParsyError):
        parser.parse("HELLO")


def test_pattern_uses_regular_expressions() -> None:
    digits = pattern(r"\d+")
    assert digits.parse("123") == "123"

    alpha = pattern(r"[a-zA-Z]+")
    assert alpha.parse("abcDEF") == "abcDEF"


def test_pattern_propagates_regex_errors() -> None:
    # An invalid regex should raise at construction time.
    with pytest.raises(re.error):
        pattern("[")


def test_integer_parses_signed_integers() -> None:
    parser = integer()
    assert isinstance(parser, Parser)
    assert parser.parse("0") == 0
    assert parser.parse("42") == 42
    assert parser.parse("-17") == -17

    with pytest.raises(ParsyError):
        parser.parse("not-an-int")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("0", 0.0),
        ("10", 10.0),
        ("3.14", 3.14),
        ("-0.5", -0.5),
        (".5", 0.5),
        ("10.", 10.0),
        ("1e3", 1000.0),
        ("-2.5E-4", -2.5e-4),
    ],
)
def test_float_num_parses_various_formats(text: str, expected: float) -> None:
    parser = float_num()
    assert pytest.approx(parser.parse(text)) == expected


def test_float_num_rejects_invalid_input() -> None:
    parser = float_num()
    with pytest.raises(ParsyError):
        parser.parse("not-a-float")


def test_word_parses_alphanumeric_words() -> None:
    parser = word()
    assert parser.parse("abc123_DEF") == "abc123_DEF"

    with pytest.raises(ParsyError):
        parser.parse("with-space ")


def test_whitespace_parses_one_or_more_spaces() -> None:
    parser = whitespace()
    assert parser.parse(" ") == " "
    assert parser.parse(" \t\n") == " \t\n"

    with pytest.raises(ParsyError):
        parser.parse("")


def test_any_char_parses_single_character() -> None:
    assert isinstance(any_char, Parser)
    assert any_char.parse("x") == "x"

    with pytest.raises(ParsyError):
        any_char.parse("")
