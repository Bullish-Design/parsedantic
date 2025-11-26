# tests/errors/test_parse_error.py
from __future__ import annotations

import parsy

from parsedantic.errors import ParseError, convert_parsy_error


class TestParseError:
    def test_creates_with_position(self) -> None:
        error = ParseError(text="hello world", index=6, expected="number")

        assert error.text == "hello world"
        assert error.index == 6
        assert error.expected == "number"
        assert error.line == 1
        assert error.column == 7

    def test_line_column_calculation(self) -> None:
        text = "line1\nline2\nline3"
        line, col = ParseError._get_line_column(text, 6)
        assert (line, col) == (2, 1)

    def test_error_dict_format(self) -> None:
        error = ParseError(text="test", index=0, expected="number", field_name="value")
        error_dict = error.error_dict()

        assert error_dict["type"] == "parse_error"
        assert error_dict["loc"] == ("value",)
        assert "ctx" in error_dict


class TestConvertParsyError:
    def test_converts_parsy_error(self) -> None:
        try:
            parsy.string("hello").parse("world")
        except parsy.ParseError as e:
            error = convert_parsy_error(e, "world")

            assert isinstance(error, ParseError)
            assert error.text == "world"
            assert error.index == 0
