# tests/core/test_parser.py
from __future__ import annotations

import parsy

from parsedantic import Parser


class TestParserWrapper:
    def test_parse_delegates_to_parsy(self) -> None:
        parser = Parser(parsy.string("hello"))
        assert parser.parse("hello") == "hello"

    def test_format_defaults_to_str(self) -> None:
        parser = Parser(parsy.string("hello"))
        assert parser.format("hello") == "hello"
        # Under the hood we simply call ``str`` when no formatter is provided.
        assert parser.format(123) == "123"  # type: ignore[arg-type]

    def test_custom_formatter_is_used(self) -> None:
        parser = Parser(parsy.string("hello"), formatter=lambda value: f"<{value}>")
        assert parser.format("hello") == "<hello>"

    def test_rshift_sequences_parsers(self) -> None:
        a = Parser(parsy.string("a"))
        b = Parser(parsy.string("b"))
        combined = a >> b

        assert isinstance(combined, Parser)
        assert combined.parse("ab") == "b"

    def test_rshift_uses_rhs_formatter(self) -> None:
        a = Parser(parsy.string("a"), formatter=lambda value: f"a:{value}")
        b = Parser(parsy.string("b"), formatter=lambda value: f"b:{value}")
        combined = a >> b

        assert combined.format("b") == "b:b"
