# tests/primitives/test_character.py
from __future__ import annotations

import pytest
import parsy

from parsedantic.primitives.character import any_char, char_from, digit, letter


class TestAnyChar:
    def test_matches_any_character(self) -> None:
        assert any_char.parse("x") == "x"

    def test_fails_on_empty(self) -> None:
        with pytest.raises(parsy.ParseError):
            any_char.parse("")


class TestCharFrom:
    def test_matches_from_set(self) -> None:
        parser = char_from("abc")
        assert parser.parse("a") == "a"

    def test_fails_outside_set(self) -> None:
        parser = char_from("abc")
        with pytest.raises(parsy.ParseError):
            parser.parse("d")


class TestLetter:
    def test_matches_letters(self) -> None:
        assert letter.parse("a") == "a"


class TestDigit:
    def test_matches_digits(self) -> None:
        assert digit.parse("5") == "5"
