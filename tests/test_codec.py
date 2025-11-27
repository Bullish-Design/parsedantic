from __future__ import annotations

from pydantic import ConfigDict

from parsedantic import ParsableModel, TextCodec


class TestTextCodecBasic:
    def test_codec_creation(self) -> None:
        """Codec should initialize for simple model."""

        class Point(ParsableModel):
            x: int
            y: int

        codec = TextCodec(Point)

        assert codec.model_class is Point
        assert codec.separator_str == " "
        assert len(codec.field_parsers) == 2

    def test_codec_parses(self) -> None:
        """Codec should parse text."""

        class Point(ParsableModel):
            x: int
            y: int

        codec = TextCodec(Point)
        point = codec.parse("10 20")

        assert point.x == 10
        assert point.y == 20

    def test_codec_serializes(self) -> None:
        """Codec should serialize instance."""

        class Point(ParsableModel):
            x: int
            y: int

        codec = TextCodec(Point)
        point = Point(x=10, y=20)
        text = codec.serialize(point)

        assert text == "10 20"

    def test_codec_respects_separator(self) -> None:
        """Codec should use configured separator."""

        class CSV(ParsableModel):
            model_config = ConfigDict(parse_separator=",")
            a: int
            b: int

        codec = TextCodec(CSV)

        assert codec.separator_str == ","

        model = CSV(a=1, b=2)
        text = codec.serialize(model)
        assert text == "1,2"


class TestTextCodecFieldIntrospection:
    def test_field_introspection(self) -> None:
        """Codec should support field-level parser access and helpers."""

        class Point(ParsableModel):
            x: int
            y: int

        # Use the same codec that ParsableModel caches internally
        codec = Point._get_codec()

        x_parser = codec.get_field_parser("x")
        assert x_parser is not None

        # Parse a single field
        value = codec.parse_field("x", "42")
        assert value == 42

        # Format a single field
        text = codec.format_field("y", 100)
        assert text == "100"
