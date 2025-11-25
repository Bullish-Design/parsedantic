# tests/test_config.py
from __future__ import annotations

from parsedantic import ParseConfig, ParsableModel, literal, pattern


def test_field_separator_literal() -> None:
    class Model(ParsableModel):
        a: int
        b: int

        class ParseConfig:
            field_separator = literal(",")

    result = Model.parse("1,2")
    assert result.a == 1
    assert result.b == 2


def test_field_separator_pattern() -> None:
    class Model(ParsableModel):
        x: str
        y: str

        class ParseConfig:
            field_separator = pattern(r"\s*-\s*")

    result = Model.parse("hello - world")
    assert result.x == "hello"
    assert result.y == "world"


def test_default_separator_is_whitespace() -> None:
    class Model(ParsableModel):
        a: int
        b: int

    result = Model.parse("10 20")
    assert result.a == 10
    assert result.b == 20


def test_nested_models_use_own_parseconfig() -> None:
    class Inner(ParsableModel):
        x: int
        y: int

        class ParseConfig:
            field_separator = literal(":")

    class Outer(ParsableModel):
        inner: Inner
        name: str

        class ParseConfig:
            field_separator = literal(" ")

    result = Outer.parse("10:20 test")
    assert result.inner.x == 10
    assert result.inner.y == 20
    assert result.name == "test"


def test_parseconfig_not_inherited_by_subclasses() -> None:
    class Base(ParsableModel):
        a: int
        b: int

        class ParseConfig:
            field_separator = literal(",")

    class Child(Base):
        c: int

    base = Base.parse("1,2")
    assert base.a == 1
    assert base.b == 2

    child = Child.parse("1 2 3")
    assert child.a == 1
    assert child.b == 2
    assert child.c == 3


def test_strict_optional_configuration() -> None:
    class Model(ParsableModel):
        required: str
        optional: int | None

        class ParseConfig:
            strict_optional = False

    result = Model.parse("text notanint")
    assert result.required == "text"
    assert result.optional is None


def test_parseconfig_defaults() -> None:
    assert ParseConfig.field_separator is None
    assert ParseConfig.strict_optional is True
    assert ParseConfig.whitespace is None
