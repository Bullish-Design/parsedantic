# tests/test_union.py
from __future__ import annotations

"""Union type handling tests (Step 9).

These tests exercise ``Union[A, B]`` / ``A | B`` support in the type-driven
parser generation, including interaction with optional types and Literal
annotations.
"""

from typing import Literal, Union

import pytest

from parsedantic.errors import ParseError
from parsedantic.generator import is_union_type
from parsedantic.models import ParsableModel


def test_union_int_or_str_prefers_int_first() -> None:
    """``int | str`` should parse numerics as ``int`` and others as ``str``."""

    class Model(ParsableModel):
        value: int | str

    result = Model.parse("123")
    assert isinstance(result, Model)
    assert result.value == 123
    assert isinstance(result.value, int)

    result2 = Model.parse("alpha")
    assert result2.value == "alpha"
    assert isinstance(result2.value, str)


def test_union_str_or_int_prefers_str_first() -> None:
    """Ordering of union members should affect which parser wins."""

    class Model(ParsableModel):
        value: str | int

    # The string alternative comes first, so numeric text should remain a str.
    result = Model.parse("123")
    assert result.value == "123"
    assert isinstance(result.value, str)

    # Non-numeric text still parses as str.
    result2 = Model.parse("alpha")
    assert result2.value == "alpha"
    assert isinstance(result2.value, str)


def test_union_of_literals_matches_any_member() -> None:
    """Union of Literal values should match any of the allowed strings."""

    class Model(ParsableModel):
        value: Literal["A"] | Literal["B"] | Literal["C"]

    assert Model.parse("A").value == "A"
    assert Model.parse("B").value == "B"
    assert Model.parse("C").value == "C"

    with pytest.raises(ParseError):
        Model.parse("D")


def test_union_multiple_primitive_types() -> None:
    """Union[int, float, str] should try each member in declaration order."""

    class Model(ParsableModel):
        value: Union[int, float, str]

    print(f"\n\nTesting Multiple Primitive Types")
    # Integer parses as int.
    result = Model.parse("10")
    print(f"\nResult 1: {result}\n")
    assert isinstance(result.value, int)
    assert result.value == 10

    # Float that is not an int parses as float.
    result2 = Model.parse("3.14")
    print(f"\nResult 2: {result2}\n")
    assert isinstance(result2.value, float)
    assert result2.value == pytest.approx(3.14)

    # Non-numeric parses as str.
    result3 = Model.parse("hello")
    print(f"\nResult 3: {result3}\n")
    assert isinstance(result3.value, str)
    assert result3.value == "hello"


def test_union_with_optional_members_respects_lenient_optional() -> None:
    """Unions that include ``None`` behave like optional unions."""

    class Model(ParsableModel):
        value: int | str | None

        class ParseConfig:
            strict_optional = False

    # Missing value yields ``None`` in lenient mode.
    result = Model.parse("")
    assert result.value is None

    # Numeric value parses as int.
    result2 = Model.parse("42")
    assert result2.value == 42
    assert isinstance(result2.value, int)

    # Non-numeric value parses as str.
    result3 = Model.parse("forty-two")
    assert result3.value == "forty-two"
    assert isinstance(result3.value, str)


def test_union_failure_when_no_alternatives_match() -> None:
    """If no union member can parse the input, a ParseError should surface."""

    class Model(ParsableModel):
        value: int | float

    with pytest.raises(ParseError):
        Model.parse("not-a-number")


def test_literal_inside_union_works_with_other_types() -> None:
    """Literal members should compose correctly with other union members."""

    class Model(ParsableModel):
        value: Literal["OK"] | Literal["ERROR"] | int

    assert Model.parse("OK").value == "OK"
    assert Model.parse("ERROR").value == "ERROR"

    # Not one of the literals, but still a valid int.
    result = Model.parse("200")
    assert result.value == 200
    assert isinstance(result.value, int)


def test_is_union_type_helper_excludes_none() -> None:
    """Helper should recognise unions and drop ``None`` members."""

    is_union, members = is_union_type(int | str | None)
    assert is_union
    # Order of non-None members should be preserved.
    assert members == (int, str)
