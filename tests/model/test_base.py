# tests/model/test_base.py
from __future__ import annotations

import pytest
from pydantic import ValidationError

from parsedantic import ParseError, Parsed, ParsableModel, integer, word


class TestParsableModel:
    def test_simple_model_parses(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        point = Point.from_text("10 20")
        assert isinstance(point, Point)
        assert point.x == 10
        assert point.y == 20

    def test_mixed_types(self) -> None:
        class Record(ParsableModel):
            name: str
            age: int
            score: float

        record = Record.from_text("alice 25 98.5")
        assert record.name == "alice"
        assert record.age == 25
        assert record.score == pytest.approx(98.5)

    def test_explicit_parsers(self) -> None:
        class Model(ParsableModel):
            name: Parsed[str, word()]
            count: Parsed[int, integer()]

        result = Model.from_text("test 42")
        assert result.name == "test"
        assert result.count == 42

    def test_empty_model(self) -> None:
        class Empty(ParsableModel):
            pass

        result = Empty.from_text("")
        assert isinstance(result, Empty)

    def test_pydantic_validation_runs(self) -> None:
        from pydantic import Field

        class Model(ParsableModel):
            value: int = Field(ge=0)

        with pytest.raises(ValidationError):
            Model.from_text("-5")

    def test_parse_error_on_invalid(self) -> None:
        class Model(ParsableModel):
            value: int

        with pytest.raises(ParseError) as exc_info:
            Model.from_text("not-a-number")

        error = exc_info.value
        assert error.text == "not-a-number"

    def test_partial_parsing(self) -> None:
        class Header(ParsableModel):
            version: int

        result, rest = Header.from_text_partial("1 extra data")
        assert result.version == 1
        assert rest == " extra data"
