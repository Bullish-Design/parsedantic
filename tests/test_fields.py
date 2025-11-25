# tests/test_fields.py
from __future__ import annotations

"""Tests for the :mod:`parsedantic.fields` module (Step 10).

These tests focus on the basic :func:`ParseField` wrapper and how explicit
parsers interact with the type-driven machinery from :mod:`parsedantic.generator`.
"""

import pytest
from parsy import ParseError as ParsyError, Parser

from parsedantic import ParseField, ParsableModel, literal, pattern
from parsedantic.generator import generate_field_parser


def test_parsefield_attaches_explicit_parser_and_overrides_type() -> None:
    """ParseField(parser=...) should take precedence over the field's type.

    The underlying type here is ``int`` which would normally use the integer
    parser. By supplying a custom parser that recognises ``"X"`` and returns
    a concrete integer value we can verify that the generated parser accepts
    input that the type-driven path would reject.
    """

    custom_parser: Parser[int] = literal("X").result(99)

    class Model(ParsableModel):
        value: int = ParseField(parser=custom_parser)

    # Access the raw field parser directly so that we are only exercising the
    # parsing layer, not Pydantic's validation.
    field_info = Model.model_fields["value"]
    parser = generate_field_parser(field_info.annotation, field_info)

    assert isinstance(parser, Parser)
    assert parser.parse("X") == 99


def test_parsefield_preserves_standard_field_kwargs() -> None:
    """Custom metadata must not interfere with normal Pydantic options."""

    class Model(ParsableModel):
        value: str = ParseField(description="example field", parser=literal("ok"))

    field_info = Model.model_fields["value"]
    assert field_info.description == "example field"

    # End-to-end parsing should still work.
    instance = Model.parse("ok")
    assert instance.value == "ok"


def test_parsefield_rejects_both_pattern_and_parser() -> None:
    """Specifying both ``pattern`` and ``parser`` is a configuration error."""
    with pytest.raises(ValueError):
        ParseField(pattern=r"\d+", parser=literal("x"))

def test_parsefield_pattern_compiles_and_overrides_type() -> None:
    """ParseField(pattern=...) should drive the field parser.

    The underlying type is ``str`` which would normally accept any
    non-whitespace token. By supplying a pattern that matches only
    uppercase letters we ensure that lowercase input is rejected.
    """

    class Model(ParsableModel):
        token: str = ParseField(pattern=r"[A-Z]+")

    field_info = Model.model_fields["token"]
    parser = generate_field_parser(field_info.annotation, field_info)

    assert parser.parse("ABC") == "ABC"
    with pytest.raises(ParsyError):
        parser.parse("abc")



def test_parsefield_sep_by_requires_list_field() -> None:
    """Using ``sep_by`` on a non-list field is a configuration error."""

    class Model(ParsableModel):
        value: int = ParseField(sep_by=literal(","))

    field_info = Model.model_fields["value"]
    with pytest.raises(TypeError):
        generate_field_parser(field_info.annotation, field_info)



def test_parsefield_sep_by_for_list_of_strings() -> None:
    """Comma-separated lists of strings using ``sep_by`` parse correctly."""

    class CsvRow(ParsableModel):
        values: list[str] = ParseField(pattern=r"[^,]+", sep_by=literal(","))

    # Zero elements.
    result = CsvRow.parse("")
    assert result.values == []

    # Single element (no comma required).
    result = CsvRow.parse("one")
    assert result.values == ["one"]

    # Multiple elements separated by commas.
    result = CsvRow.parse("a,b,c")
    assert result.values == ["a", "b", "c"]



def test_parsefield_sep_by_with_pattern_separator_for_ints() -> None:
    """Separator may be an arbitrary parser, typically a regex pattern."""

    class Numbers(ParsableModel):
        nums: list[int] = ParseField(sep_by=pattern(r"\s*,\s*"))

    # Empty input yields an empty list.
    result = Numbers.parse("")
    assert result.nums == []

    # Single element.
    result = Numbers.parse("10")
    assert result.nums == [10]

    # Multiple elements with flexible whitespace around commas.
    result = Numbers.parse("1, 2,   3")
    assert result.nums == [1, 2, 3]



def test_parsefield_pattern_and_sep_by_for_mixed_model() -> None:
    """Pattern controls list elements while ``sep_by`` separates them."""

    class MixedModel(ParsableModel):
        id: int
        tags: list[str] = ParseField(pattern=r"\w+", sep_by=literal(" "))

    result = MixedModel.parse("10 foo bar baz")
    assert result.id == 10
    assert result.tags == ["foo", "bar", "baz"]

