# tests/test_optional.py
from __future__ import annotations

"""Optional type handling tests (Step 7).

These tests exercise ``Optional[T]`` / ``T | None`` support in the type-driven
parser generation and its interaction with ``ParseConfig.strict_optional``.
"""

from typing import Optional

import pytest

from parsedantic.errors import ParseError
from parsedantic.models import ParsableModel


def test_optional_int_valid_input() -> None:
    """A simple ``Optional[int]`` field should parse an integer value."""

    class Model(ParsableModel):
        value: Optional[int]

    # Default configuration uses strict optional behaviour.
    result = Model.parse("123")
    assert isinstance(result, Model)
    assert result.value == 123


def test_optional_missing_strict_mode_errors() -> None:
    """Missing optional field should fail in strict mode."""

    class Model(ParsableModel):
        value: int | None

    with pytest.raises(ParseError):
        Model.parse("")  # no value provided


def test_optional_missing_lenient_mode_is_none() -> None:
    """Missing optional field should yield ``None`` in lenient mode."""

    class Model(ParsableModel):
        value: int | None

        class ParseConfig:
            strict_optional = False

    result = Model.parse("")
    assert result.value is None


def test_optional_type_strict_mode_with_invalid_value() -> None:
    """Invalid optional value should raise in strict mode."""

    class Model(ParsableModel):
        required: str
        optional: int | None

        class ParseConfig:
            strict_optional = True

    with pytest.raises(ParseError):
        Model.parse("text notanint")


def test_optional_type_lenient_mode_with_invalid_value() -> None:
    """Invalid optional value should become ``None`` in lenient mode."""

    class Model(ParsableModel):
        required: str
        optional: int | None

        class ParseConfig:
            strict_optional = False

    result = Model.parse("text notanint")
    assert result.required == "text"
    assert result.optional is None


def test_nested_optional_type_lenient_mode() -> None:
    """Nested ``Optional[Optional[T]]`` should behave sensibly."""

    class Model(ParsableModel):
        value: Optional[Optional[int]]

        class ParseConfig:
            strict_optional = False

    # Completely missing value -> None.
    result = Model.parse("")
    assert result.value is None

    # Present and valid value -> inner integer.
    result2 = Model.parse("5")
    assert result2.value == 5


def test_optional_in_multi_field_model_lenient_mode() -> None:
    """Optional second field should be skippable in lenient mode."""

    class Model(ParsableModel):
        first: str
        maybe: int | None

        class ParseConfig:
            strict_optional = False

    # Optional value omitted.
    result = Model.parse("alpha")
    assert result.first == "alpha"
    assert result.maybe is None

    # Optional present and valid.
    result2 = Model.parse("alpha 10")
    assert result2.first == "alpha"
    assert result2.maybe == 10
