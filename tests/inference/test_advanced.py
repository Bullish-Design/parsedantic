# tests/inference/test_advanced.py
from __future__ import annotations

from typing import Literal

import pytest
import parsy

from parsedantic import ParsableModel
from parsedantic.inference import infer_parser
from parsedantic.inference.advanced import is_literal, is_parsable_model


class TestIsLiteral:
    def test_detects_literal_strings(self) -> None:
        is_lit, values = is_literal(Literal["INFO", "WARN"])
        assert is_lit is True
        assert values == ("INFO", "WARN")

    def test_non_literal_returns_false(self) -> None:
        is_lit, values = is_literal(int)
        assert is_lit is False
        assert values == ()


class TestLiteralInference:
    def test_infers_literal_string_parser(self) -> None:
        parser = infer_parser(Literal["INFO", "WARN"])
        assert parser is not None
        assert parser.parse("INFO") == "INFO"
        assert parser.parse("WARN") == "WARN"
        with pytest.raises(parsy.ParseError):
            parser.parse("DEBUG")

    def test_non_string_literal_raises(self) -> None:
        with pytest.raises(TypeError):
            infer_parser(Literal[1, 2])  # type: ignore[arg-type]


class TestIsParsableModel:
    def test_detects_parsable_model_subclass(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        assert is_parsable_model(Point) is True

    def test_rejects_non_model(self) -> None:
        assert is_parsable_model(int) is False
        assert is_parsable_model("not-a-type") is False  # type: ignore[arg-type]


class TestNestedModelInference:
    def test_nested_model_parser_direct(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        parser = infer_parser(Point)
        assert parser is not None

        result = parser.parse("1 2")
        assert isinstance(result, Point)
        assert result.x == 1
        assert result.y == 2

        formatted = parser.format(Point(x=3, y=4))
        assert formatted == "3 4"

    def test_nested_model_inside_other_model(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        class Line(ParsableModel):
            start: Point
            end: Point

        line = Line.from_text("1 2 3 4")
        assert isinstance(line.start, Point)
        assert isinstance(line.end, Point)
        assert line.start.x == 1
        assert line.start.y == 2
        assert line.end.x == 3
        assert line.end.y == 4

        text = line.to_text()
        assert text == "1 2 3 4"

        parsed = Line.from_text(text)
        assert parsed.start.x == 1
        assert parsed.end.y == 4
