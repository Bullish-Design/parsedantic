# tests/test_builder.py
from __future__ import annotations

import pytest

from parsedantic import ParsableModel, ParseError, parser_builder, literal, pattern, any_char


class TestParserBuilder:
    """Tests for the @parser_builder decorator on ParsableModel subclasses."""

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
        assert isinstance(result, Hollerith)
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

    def test_parser_builder_invalid_usage_raises(self) -> None:
        """Non-generator functions should be rejected early."""

        with pytest.raises(TypeError):

            @parser_builder
            def not_a_generator():
                return 1  # pragma: no cover - should never be called

            # Force binding/usage so that decorator is exercised
            _ = not_a_generator
