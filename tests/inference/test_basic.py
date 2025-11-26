# tests/inference/test_basic.py
from __future__ import annotations

import pytest

from parsedantic import Parsed, integer, word
from parsedantic.inference import get_parser_for_field, infer_parser


class TestInferParser:
    def test_infer_int(self) -> None:
        parser = infer_parser(int)
        assert parser is not None
        assert parser.parse("42") == 42

    def test_infer_float(self) -> None:
        parser = infer_parser(float)
        assert parser is not None
        assert parser.parse("3.14") == pytest.approx(3.14)

    def test_infer_str(self) -> None:
        parser = infer_parser(str)
        assert parser is not None
        assert parser.parse("hello") == "hello"

    def test_infer_unknown_returns_none(self) -> None:
        assert infer_parser(bool) is None
        assert infer_parser(dict) is None


class TestGetParserForField:
    def test_explicit_parser_priority(self) -> None:
        custom = word()
        annotation = Parsed[str, custom]
        parser = get_parser_for_field(annotation)
        assert parser is custom

    def test_fallback_to_inference(self) -> None:
        parser = get_parser_for_field(int)
        assert parser is not None
        assert parser.parse("42") == 42

    def test_returns_none_for_unknown(self) -> None:
        assert get_parser_for_field(bool) is None
