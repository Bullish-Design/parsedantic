# tests/test_list.py
from __future__ import annotations

"""List type handling tests (Step 8).

These tests exercise ``list[T]`` support in the type-driven parser generation.
"""

from typing import Optional

import pytest

from parsedantic.models import ParsableModel


def test_simple_list_of_ints_parses_multiple_values() -> None:
    class Model(ParsableModel):
        values: list[int]

    result = Model.parse("1 2 3 4")
    assert isinstance(result, Model)
    assert result.values == [1, 2, 3, 4]


def test_list_of_strings_allows_empty_input() -> None:
    class Model(ParsableModel):
        items: list[str]

    result = Model.parse("")
    assert isinstance(result, Model)
    assert result.items == []


def test_list_field_after_scalar_field_uses_separator() -> None:
    class Model(ParsableModel):
        head: str
        numbers: list[int]

    result = Model.parse("start 10 20 30")
    assert result.head == "start"
    assert result.numbers == [10, 20, 30]


def test_list_field_between_scalars_consumes_greedily() -> None:
    class Model(ParsableModel):
        prefix: str
        numbers: list[int]
        suffix: str

    result = Model.parse("begin 1 2 3 end")
    assert result.prefix == "begin"
    assert result.numbers == [1, 2, 3]
    assert result.suffix == "end"


def test_bare_list_annotation_raises_type_error() -> None:
    class Model(ParsableModel):
        # Deliberately omit element type.
        values: list  # type: ignore[valid-type]

    with pytest.raises(TypeError):
        Model.parse("1 2 3")


def test_list_of_optional_ints_parses_as_list_of_ints() -> None:
    class Model(ParsableModel):
        values: list[Optional[int]]

    result = Model.parse("1 2 3")
    assert result.values == [1, 2, 3]
