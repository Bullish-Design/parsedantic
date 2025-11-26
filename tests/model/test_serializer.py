# tests/model/test_serializer.py
from __future__ import annotations

import pytest

from parsedantic import ParsableModel


class TestSerialization:
    def test_simple_serialization(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        point = Point(x=10, y=20)
        assert point.to_text() == "10 20"

    def test_roundtrip(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        original = "10 20"
        point = Point.from_text(original)
        serialized = point.to_text()
        assert serialized == original

    def test_mixed_types(self) -> None:
        class Record(ParsableModel):
            name: str
            age: int
            score: float

        record = Record(name="alice", age=25, score=98.5)
        text = record.to_text()

        parsed = Record.from_text(text)
        assert parsed.name == "alice"
        assert parsed.age == 25
        assert parsed.score == pytest.approx(98.5)

    def test_list_serialization(self) -> None:
        class Model(ParsableModel):
            values: list[int]

        model = Model(values=[1, 2, 3])
        text = model.to_text()

        parsed = Model.from_text(text)
        assert parsed.values == [1, 2, 3]

    def test_multiple_roundtrips(self) -> None:
        class Point(ParsableModel):
            x: int
            y: int

        original = "10 20"

        point1 = Point.from_text(original)
        text1 = point1.to_text()

        point2 = Point.from_text(text1)
        text2 = point2.to_text()

        assert text1 == text2
