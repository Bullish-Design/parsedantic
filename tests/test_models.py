# tests/test_models.py
from __future__ import annotations

"""Tests for the :mod:`parsedantic.models` module (Step 4).

These tests exercise the ``ParsableModel`` skeleton, ensuring that parsing
delegates to a cached parser, wraps parsy errors in our :class:`ParseError`,
and still runs full Pydantic validation on the parsed data.
"""

from typing import Any, ClassVar, Dict, List, Type

import pytest
from parsy import string
from pydantic import BaseModel, ValidationError

from parsedantic import literal
from parsedantic.errors import ParseError
from parsedantic.models import ParsableModel


def test_parse_calls_get_parser_and_uses_result() -> None:
    """``parse`` should obtain its parser via ``_get_parser`` and use it."""

    calls: List[Type[ParsableModel]] = []

    class DummyParser:
        def __init__(self) -> None:
            self.seen: List[str] = []

        def parse(self, text: str) -> Dict[str, Any]:
            self.seen.append(text)
            return {"value": 42}

    parser = DummyParser()

    class Model(ParsableModel):
        value: int

    # Monkeypatch ``_get_parser`` to record the call and return our dummy parser.
    @classmethod
    def fake_get_parser(cls: Type[ParsableModel]) -> DummyParser:  # type: ignore[override]
        calls.append(cls)
        return parser

    Model._get_parser = fake_get_parser  # type: ignore[assignment]

    result = Model.parse("input text")
    assert isinstance(result, Model)
    assert result.value == 42
    assert calls == [Model]
    assert parser.seen == ["input text"]


def test_parser_is_cached_between_calls() -> None:
    """The first call should build a parser and subsequent calls reuse it."""

    class Model(ParsableModel):
        value: int

        build_calls: ClassVar[int] = 0
        last_parser: ClassVar[Any | None] = None

        @classmethod
        def _build_parser(cls) -> Any:  # type: ignore[override]
            cls.build_calls += 1

            class DummyParser:
                def __init__(self) -> None:
                    self.calls: List[str] = []

                def parse(self, text: str) -> Dict[str, Any]:
                    self.calls.append(text)
                    return {"value": 7}

            parser = DummyParser()
            cls.last_parser = parser
            return parser

    # Ensure a clean cache for this test.
    ParsableModel._parser_cache.clear()

    first = Model.parse("one")
    second = Model.parse("two")

    assert isinstance(first, Model)
    assert isinstance(second, Model)
    assert Model.build_calls == 1
    assert Model.last_parser is not None
    assert Model.last_parser.calls == ["one", "two"]  # type: ignore[union-attr]


def test_parsy_parse_error_is_wrapped_in_parseerror() -> None:
    """parsy ``ParseError`` should be converted into our own ``ParseError``."""

    class Model(ParsableModel):
        value: int

        @classmethod
        def _build_parser(cls) -> Any:  # type: ignore[override]
            # A parser that only accepts the literal ``"ok"`` and fails otherwise.
            return string("ok").result({"value": 1})

    ParsableModel._parser_cache.clear()

    with pytest.raises(ParseError) as excinfo:
        Model.parse("bad")

    err = excinfo.value
    assert isinstance(err, ParseError)
    # The error should reference the original input text.
    assert err.text == "bad"
    # Index and expected are derived from the underlying parsy error; make
    # sure they are sensible.
    assert isinstance(err.index, int)
    assert err.index >= 0
    assert isinstance(err.expected, str)
    assert err.expected != ""


def test_validation_runs_after_parsing() -> None:
    """Parsed data should still be validated by Pydantic."""

    class Model(ParsableModel):
        value: int

        @classmethod
        def _build_parser(cls) -> Any:  # type: ignore[override]
            # The parser claims ``value`` is a string, which Pydantic will reject.
            return string("x").result({"value": "not-an-int"})

    ParsableModel._parser_cache.clear()

    with pytest.raises(ValidationError):
        Model.parse("x")


def test_parsablemodel_satisfies_pydantic_basemodel_behaviour() -> None:
    """ParsableModel should still behave like a normal BaseModel when constructed
    directly, independent of the parsing machinery.
    """

    class Model(ParsableModel):
        value: int

    direct = Model(value=5)
    assert isinstance(direct, BaseModel)
    assert direct.value == 5


def test_type_driven_parsing_simple_model() -> None:
    """Models with basic annotations should parse using type-driven generation."""

    class Model(ParsableModel):
        text: str
        count: int
        value: float

    ParsableModel._parser_cache.clear()
    model = Model.parse("hello 3 3.5")
    assert isinstance(model, Model)
    assert model.text == "hello"
    assert model.count == 3
    assert model.value == 3.5


def test_type_driven_parsing_with_field_separator() -> None:
    """Type-driven parsing should honour ``ParseConfig.field_separator``."""

    class CsvRecord(ParsableModel):
        a: int
        b: int

        class ParseConfig:
            field_separator = literal(",")

    ParsableModel._parser_cache.clear()
    record = CsvRecord.parse("10,20")
    assert isinstance(record, CsvRecord)
    assert record.a == 10
    assert record.b == 20




def test_optional_type_strict_mode_in_models() -> None:
    """Optional field should raise on invalid value when strict."""

    class Model(ParsableModel):
        required: str
        optional: int | None

        class ParseConfig:
            strict_optional = True

    with pytest.raises(ParseError):
        Model.parse("text notanint")


def test_optional_type_lenient_mode_in_models() -> None:
    """Optional field should yield ``None`` on invalid value when lenient."""

    class Model(ParsableModel):
        required: str
        optional: int | None

        class ParseConfig:
            strict_optional = False

    result = Model.parse("text notanint")
    assert result.required == "text"
    assert result.optional is None
def test_type_driven_parse_failure_raises_parseerror() -> None:
    """Invalid input should raise our :class:`ParseError` via ``parse``."""

    class Model(ParsableModel):
        value: int

    ParsableModel._parser_cache.clear()
    with pytest.raises(ParseError):
        Model.parse("not-an-int")
