# tests/test_caching.py
from __future__ import annotations

"""Caching behaviour tests for :mod:`parsedantic.models` and
:mod:`parsedantic.generator` (Step 6).

These tests verify that model parsers are cached per subclass and that
``build_model_parser`` performs basic type-level parser caching.
"""

from typing import Any, ClassVar, Dict

import time

from parsy import Parser, string

from parsedantic.generator import build_model_parser, generate_field_parser
from parsedantic.models import ParsableModel


class CounterModel(ParsableModel):
    """Model whose parser construction can be counted in tests."""

    value: str

    _build_calls: ClassVar[int] = 0

    @classmethod
    def _build_parser(cls) -> Parser[Dict[str, Any]]:
        cls._build_calls += 1
        # Very small parser: expect the literal ``x`` and return mapping.
        return string("x").result({"value": "x"})


def test_parser_cached_on_get_parser_calls() -> None:
    """``_get_parser`` should build the parser only once per class."""

    CounterModel._clear_parser_cache()
    CounterModel._build_calls = 0

    parser1 = CounterModel._get_parser()
    parser2 = CounterModel._get_parser()

    assert parser1 is parser2
    assert CounterModel._build_calls == 1


def test_parse_uses_cached_parser() -> None:
    """Multiple ``parse`` calls should reuse the same parser instance."""

    CounterModel._clear_parser_cache()
    CounterModel._build_calls = 0

    first = CounterModel.parse("x")
    second = CounterModel.parse("x")

    assert first.value == "x"
    assert second.value == "x"
    assert CounterModel._build_calls == 1


def test_different_models_have_distinct_cached_parsers() -> None:
    """Each concrete ``ParsableModel`` subclass gets its own parser."""

    class ModelA(ParsableModel):
        field: int

    class ModelB(ParsableModel):
        field: int

    ModelA._clear_parser_cache()
    ModelB._clear_parser_cache()

    parser_a = ModelA._get_parser()
    parser_b = ModelB._get_parser()

    assert parser_a is not parser_b


def test_subclass_uses_own_parser_not_parent() -> None:
    """Subclasses must not reuse the parent's cached parser instance."""

    class Parent(ParsableModel):
        value: int

    class Child(Parent):
        pass

    Parent._clear_parser_cache()
    Child._clear_parser_cache()

    parent_parser = Parent._get_parser()
    child_parser = Child._get_parser()

    assert parent_parser is not child_parser


def test_clear_parser_cache_forces_rebuild() -> None:
    """``_clear_parser_cache`` should drop the cached parser for the class."""

    CounterModel._clear_parser_cache()
    CounterModel._build_calls = 0

    first = CounterModel._get_parser()
    assert CounterModel._build_calls == 1

    CounterModel._clear_parser_cache()
    second = CounterModel._get_parser()
    assert CounterModel._build_calls == 2

    assert first is not second


def test_build_model_parser_reuses_field_parsers(monkeypatch) -> None:
    """``build_model_parser`` should avoid regenerating parsers for
    identical field types within a single model.
    """

    call_count = 0
    original = generate_field_parser

    def counting_generate_field_parser(
        field_type: Any, field_info: Any, **kwargs: Any
    ) -> Parser[Any]:
        nonlocal call_count
        call_count += 1
        return original(field_type, field_info)

    monkeypatch.setattr(
        "parsedantic.generator.generate_field_parser",
        counting_generate_field_parser,
    )

    class Pair(ParsableModel):
        first: int
        second: int

    Pair._clear_parser_cache()
    build_model_parser(Pair)

    # Even though there are two ``int`` fields, the underlying field
    # parser should have been created exactly once.
    assert call_count == 1


def test_cached_parser_enables_fast_repeated_parses() -> None:
    """Repeated parses of the same model should be inexpensive.

    This test does not enforce hard timing guarantees but guards
    against accidental behaviour that would rebuild parsers on each
    call by asserting that the number of build calls remains constant
    even for many parses.
    """

    CounterModel._clear_parser_cache()
    CounterModel._build_calls = 0

    # First parse triggers parser construction.
    start = time.perf_counter()
    CounterModel.parse("x")
    first_duration = time.perf_counter() - start
    assert CounterModel._build_calls == 1

    # Many subsequent parses should reuse the cached parser.
    for _ in range(100):
        CounterModel.parse("x")
    assert CounterModel._build_calls == 1

    # We record the timings primarily for debugging; no strict assertion
    # on the ratio is made to avoid flaky tests.
    start = time.perf_counter()
    CounterModel.parse("x")
    second_duration = time.perf_counter() - start

    # Basic sanity: second_duration should be a positive float.
    assert second_duration > 0.0
