# tests/inference/test_advanced.py
from __future__ import annotations

from typing import Literal

import pytest

from parsedantic import ParsableModel
from parsedantic.inference import infer_parser
from parsedantic.inference.inference import _is_literal as is_literal
from parsedantic.inference.inference import _is_parsable_model as is_parsable_model


class TestIsLiteral:
    def test_detects_literal_strings(self) -> None:
        is_lit, values = is_literal(Literal["OK", "ERROR"])
        assert is_lit is True
        assert set(values) == {"OK", "ERROR"}

    def test_non_literal_returns_false(self) -> None:
        is_lit, _ = is_literal(int)
        assert is_lit is False


class TestLiteralInference:
    def test_infers_literal_string_parser(self) -> None:
        parser = infer_parser(Literal["OK", "ERROR"])
        assert parser is not None
        assert parser.parse("OK") == "OK"
        assert parser.parse("ERROR") == "ERROR"

    def test_non_string_literal_raises(self) -> None:
        with pytest.raises(TypeError, match="string values"):
            infer_parser(Literal[1, 2, 3])


class TestIsParsableModel:
    def test_detects_parsable_model_subclass(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        assert is_parsable_model(Point) is True

    def test_rejects_non_model(self) -> None:
        assert is_parsable_model(int) is False
        assert is_parsable_model(str) is False


class TestNestedModelInference:
    def test_nested_model_parser_direct(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        parser = infer_parser(Point)
        assert parser is not None

        result = parser.parse("10 20")
        assert isinstance(result, Point)
        assert result.x == 10
        assert result.y == 20

    def test_nested_model_inside_other_model(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        class Line(ParsableModel):
            start: Point
            end: Point

        line = Line.from_text("1 2 3 4")
        assert line.start.x == 1
        assert line.start.y == 2
        assert line.end.x == 3
        assert line.end.y == 4
