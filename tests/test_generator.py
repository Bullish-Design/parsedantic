# tests/test_generator.py
from __future__ import annotations

"""Tests for the :mod:`parsedantic.generator` module (Step 5).

These tests exercise type-driven parser generation for simple field types and
model-level parser construction.
"""

import pytest
from parsy import Parser
from pydantic import Field as PydanticField

from parsedantic.generator import build_model_parser, generate_field_parser
from parsedantic.models import ParsableModel
from parsedantic.parsers import literal


def test_generate_field_parser_for_str_int_float() -> None:
    """Primitive scalar types should get the expected parsers."""
    field_info = PydanticField()

    str_parser = generate_field_parser(str, field_info)
    int_parser = generate_field_parser(int, field_info)
    float_parser = generate_field_parser(float, field_info)

    assert isinstance(str_parser, Parser)
    assert isinstance(int_parser, Parser)
    assert isinstance(float_parser, Parser)

    assert str_parser.parse("token") == "token"
    assert int_parser.parse("-42") == -42
    assert float_parser.parse("3.5") == 3.5


def test_generate_field_parser_unsupported_type_raises() -> None:
    """Types without generation support should raise ``NotImplementedError``."""
    field_info = PydanticField()
    with pytest.raises(NotImplementedError):
        generate_field_parser(bool, field_info)


def test_build_model_parser_simple_model() -> None:
    """A simple model with primitive fields should parse using whitespace."""

    class Point(ParsableModel):
        x: int
        y: float

    parser = build_model_parser(Point)
    result = parser.parse("10 2.5")
    assert result == {"x": 10, "y": 2.5}

    # ``ParsableModel.parse`` should round-trip through model validation.
    point = Point.parse("10 2.5")
    assert isinstance(point, Point)
    assert point.x == 10
    assert point.y == 2.5


def test_build_model_parser_respects_field_separator_config() -> None:
    """``ParseConfig.field_separator`` should be honoured when present."""

    class CsvModel(ParsableModel):
        a: int
        b: int

        class ParseConfig:
            field_separator = literal(",")

    parser = build_model_parser(CsvModel)
    data = parser.parse("1,2")
    assert data == {"a": 1, "b": 2}

    model = CsvModel.parse("1,2")
    assert isinstance(model, CsvModel)
    assert model.a == 1
    assert model.b == 2


def test_build_model_parser_for_model_with_no_fields() -> None:
    """Models with no fields should parse to an empty mapping."""

    class Empty(ParsableModel):
        pass

    parser = build_model_parser(Empty)

    # No fields means no input is consumed; the empty string parses successfully.
    result = parser.parse("")

    assert result == {}
    instance = Empty.parse("")
    assert isinstance(instance, Empty)
