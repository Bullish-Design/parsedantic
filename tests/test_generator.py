# tests/test_generator.py
from __future__ import annotations

import parsy
import pytest

from parsedantic import any_char, generate, integer, literal


class TestGenerateDecorator:
    def test_requires_generator_function(self) -> None:
        def not_a_generator() -> int:
            return 1

        with pytest.raises(TypeError, match="generator function"):
            from parsedantic.generator import generate as raw_generate

            raw_generate(not_a_generator)

    def test_simple_composed_parser(self) -> None:
        @generate
        def pair():
            first = (yield integer())
            yield literal(" ")
            second = (yield integer())
            return first, second

        parser = pair()
        assert parser.parse("1 2") == (1, 2)

    def test_works_with_raw_parsy_parsers(self) -> None:
        @generate
        def ab():
            first = (yield parsy.string("a"))
            second = (yield parsy.string("b"))
            return first + second

        parser = ab()
        assert parser.parse("ab") == "ab"

    def test_preserves_function_metadata(self) -> None:
        @generate
        def documented():
            """Example parser."""
            _ = (yield any_char)
            return "ok"

        parser_factory = documented

        assert parser_factory.__name__ == "documented"
        assert parser_factory.__doc__ == "Example parser."

        parser = parser_factory()
        assert parser.parse("x") == "ok"
