# tests/inference/test_container.py
from __future__ import annotations

from typing import Optional

import pytest

from parsedantic.inference import infer_parser
from parsedantic.inference.inference import _is_list, _is_optional, _is_union


class TestIsOptional:
    def test_detects_optional(self) -> None:
        assert _is_optional(Optional[int]) is True

    def test_detects_pipe_none(self) -> None:
        assert _is_optional(int | None) is True


class TestIsUnion:
    def test_detects_union(self) -> None:
        assert _is_union(int | str) is True


class TestIsList:
    def test_detects_list_with_type(self) -> None:
        assert _is_list(list[int]) is True


class TestInferContainer:
    def test_optional_int(self) -> None:
        parser = infer_parser(Optional[int])
        assert parser is not None
        assert parser.parse("42") == 42
        assert parser.parse("") is None

    def test_union_int_str(self) -> None:
        parser = infer_parser(int | str)
        assert parser is not None
        result = parser.parse("42")
        assert result == 42
        assert isinstance(result, int)

    def test_list_int(self) -> None:
        parser = infer_parser(list[int])
        assert parser is not None
        assert parser.parse("1 2 3") == [1, 2, 3]

    def test_list_without_element_raises(self) -> None:
        with pytest.raises(TypeError, match="element type"):
            infer_parser(list)