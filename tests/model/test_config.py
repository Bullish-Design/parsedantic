# tests/model/test_config.py
from __future__ import annotations

import pytest
from pydantic import ConfigDict

from parsedantic import ConfigDict as ParsedanticConfigDictAlias  # ensure re-export
from parsedantic import ParsableModel
from parsedantic.config import get_field_separator
from parsedantic.primitives import pattern


class TestGetFieldSeparator:
    def test_default_whitespace_separator(self) -> None:
        class Model(ParsableModel):
            x: int
            y: int

        sep = get_field_separator(Model)
        # Should parse one or more whitespace characters
        assert sep.parse("   ") == "   "

    def test_string_separator_used_for_parsing(self) -> None:
        class Model(ParsableModel):
            model_config = ConfigDict(parse_separator=",")

            a: int
            b: int

        result = Model.from_text("1,2")
        assert result.a == 1
        assert result.b == 2

    def test_parser_separator_used_for_parsing(self) -> None:
        class Model(ParsableModel):
            model_config = ConfigDict(parse_separator=pattern(r"\s*,\s*"))

            a: int
            b: int

        result = Model.from_text("1 , 2")
        assert result.a == 1
        assert result.b == 2

    def test_invalid_separator_type_raises(self) -> None:
        class Model(ParsableModel):
            # type: ignore[assignment]
            model_config = ConfigDict(parse_separator=123)

            value: int

        with pytest.raises(TypeError, match="parse_separator must be Parser or str"):
            Model.from_text("1")


class TestConfigDictExport:
    def test_configdict_reexported(self) -> None:
        # Parsedantic must re-export ConfigDict for convenience
        assert ParsedanticConfigDictAlias is ConfigDict
