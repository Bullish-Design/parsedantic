# tests/integration/test_roundtrip.py
from __future__ import annotations

from pydantic import ConfigDict

from parsedantic import ParsableModel


class TestRoundtrip:
    def test_simple_roundtrip(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        original = "10 20"
        parsed = Point.from_text(original)
        assert parsed.x == 10
        assert parsed.y == 20
        assert parsed.to_text() == original

    def test_nested_model_roundtrip(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        class Line(ParsableModel):
            start: Point
            end: Point

        line = Line(
            start=Point(x=1, y=2),
            end=Point(x=3, y=4),
        )

        text = line.to_text()
        parsed = Line.from_text(text)

        assert parsed.start.x == 1
        assert parsed.start.y == 2
        assert parsed.end.x == 3
        assert parsed.end.y == 4

    def test_custom_separator_roundtrip(self) -> None:
        class Model(ParsableModel):
            model_config = ConfigDict(parse_separator=",")

            a: int
            b: int

        model = Model(a=1, b=2)
        text = model.to_text()
        assert text == "1,2"

        parsed = Model.from_text(text)
        assert parsed.a == 1
        assert parsed.b == 2
