# tests/test_composition.py
from __future__ import annotations

"""Nested ``ParsableModel`` composition tests (Step 12).

These tests exercise automatic detection of nested :class:`ParsableModel`
fields and ensure that their parsers compose correctly with the surrounding
model, including interaction with lists, unions and ``ParseConfig``.
"""

from typing import Literal

from parsedantic import ParseField, ParsableModel, literal


def test_simple_nested_model_parses_correctly() -> None:
    """A model field typed as another ``ParsableModel`` should compose."""

    class Inner(ParsableModel):
        x: int
        y: int

    class Outer(ParsableModel):
        inner: Inner
        name: str

    result = Outer.parse("1 2 outer")
    assert isinstance(result, Outer)
    assert isinstance(result.inner, Inner)
    assert result.inner.x == 1
    assert result.inner.y == 2
    assert result.name == "outer"


def test_multiple_nested_models_line_of_points() -> None:
    """Multiple nested models should compose sequentially."""

    class Point(ParsableModel):
        x: int
        y: int

    class Line(ParsableModel):
        start: Point
        end: Point

    result = Line.parse("1 2 3 4")
    assert isinstance(result.start, Point)
    assert isinstance(result.end, Point)
    assert (result.start.x, result.start.y) == (1, 2)
    assert (result.end.x, result.end.y) == (3, 4)


def test_deeply_nested_models_three_levels() -> None:
    """Composition should work through multiple nesting levels."""

    class A(ParsableModel):
        value: int

    class B(ParsableModel):
        a: A
        name: str

    class C(ParsableModel):
        b: B
        tag: str

    result = C.parse("99 inner outertag")
    assert isinstance(result.b, B)
    assert isinstance(result.b.a, A)
    assert result.b.a.value == 99
    assert result.b.name == "inner"
    assert result.tag == "outertag"


def test_union_of_parsable_models_uses_nested_parsers() -> None:
    """``Union[ModelA, ModelB]`` should try each nested model parser."""

    class TypeA(ParsableModel):
        kind: Literal["A"] = "A"
        a_field: int

    class TypeB(ParsableModel):
        kind: Literal["B"] = "B"
        b_field: str

    class Container(ParsableModel):
        item: TypeA | TypeB

    first = Container.parse("A 10")
    assert isinstance(first.item, TypeA)
    assert first.item.a_field == 10

    second = Container.parse("B value")
    assert isinstance(second.item, TypeB)
    assert second.item.b_field == "value"


def test_list_of_nested_models_parses_sequence() -> None:
    """``list[ParsableModel]`` fields should parse repeated nested values."""

    class Item(ParsableModel):
        name: str
        value: int

        class ParseConfig:
            # Use a distinct separator so list parsing remains unambiguous.
            field_separator = literal("=")

    class Container(ParsableModel):
        items: list[Item]

    result = Container.parse("foo=1 bar=2 baz=3")
    assert len(result.items) == 3
    assert [item.name for item in result.items] == ["foo", "bar", "baz"]
    assert [item.value for item in result.items] == [1, 2, 3]


def test_nested_model_respects_own_parseconfig() -> None:
    """Inner model should honour its own ``ParseConfig`` settings."""

    class Inner(ParsableModel):
        left: int
        right: int

        class ParseConfig:
            field_separator = literal(":")

    class Outer(ParsableModel):
        inner: Inner
        label: str

        class ParseConfig:
            field_separator = literal(" ")

    result = Outer.parse("10:20 label")
    assert isinstance(result.inner, Inner)
    assert (result.inner.left, result.inner.right) == (10, 20)
    assert result.label == "label"


def test_empty_nested_model_field() -> None:
    """Nested models with no fields should still compose correctly."""

    class Empty(ParsableModel):
        pass

    class Wrapper(ParsableModel):
        inner: Empty

    result = Wrapper.parse("")

    assert isinstance(result, Wrapper)
    assert isinstance(result.inner, Empty)
