# tests/test_builder.py
from __future__ import annotations

"""Tests for the :func:`parser_builder` decorator (Step 15).

These tests exercise the generator-style parser construction for complex
patterns that do not fit the declarative, field-driven model.
"""

from parsedantic import ParsableModel, any_char, literal, parser_builder, pattern


class TestParserBuilder:
    def test_parser_builder_decorator(self) -> None:
        """Test @parser_builder for complex parsing (Hollerith-style)."""

        class Hollerith(ParsableModel):
            content: str

            @parser_builder
            @classmethod
            def _build_parser(cls):
                length = yield pattern(r"\d+").map(int)
                yield literal("H")
                chars = yield any_char.times(length)
                return {"content": "".join(chars)}

        result = Hollerith.parse("5Hhello")
        assert result.content == "hello"

    def test_parser_builder_overrides_fields(self) -> None:
        """Test @parser_builder completely overrides field parsing."""

        class Model(ParsableModel):
            x: int  # This would normally parse an int

            @parser_builder
            @classmethod
            def _build_parser(cls):
                # But we override to parse string "X"
                yield literal("X")
                return {"x": 99}

        result = Model.parse("X")
        assert result.x == 99
