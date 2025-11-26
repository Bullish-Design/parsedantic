# tests/primitives/test_control.py
from __future__ import annotations

import pytest
import parsy

from parsedantic.primitives.control import eof, fail, index, peek, success
from parsedantic.primitives.text import literal


class TestSuccess:
    def test_always_succeeds(self) -> None:
        parser = success(42)
        assert parser.parse("") == 42


class TestFail:
    def test_always_fails(self) -> None:
        parser = fail("something")
        with pytest.raises(parsy.ParseError):
            parser.parse("anything")


class TestEof:
    def test_matches_end(self) -> None:
        parser = eof()
        assert parser.parse("") is None


class TestPeek:
    def test_lookahead(self) -> None:
        parser = peek(literal("x"))
        value, rest = parser.parse_partial("xyz")
        assert value == "x"
        assert rest == "xyz"


class TestIndex:
    def test_returns_position(self) -> None:
        parser = index()
        assert parser.parse("") == 0
