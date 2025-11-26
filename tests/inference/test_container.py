# tests/inference/test_container.py
from __future__ import annotations

from typing import Optional

import pytest

from parsedantic.inference import infer_parser
from parsedantic.inference.inference import _is_list as is_list
from parsedantic.inference.inference import _is_optional as is_optional
from parsedantic.inference.inference import _is_union as is_union


class TestIsOptional:
    def test_detects_optional(self) -> None:
        is_opt, inner = is_optional(Optional[int])
        assert is_opt is True
        assert inner is int

    def test_detects_pipe_none(self) -> None:
        is_opt, inner = is_optional(int | None)
        assert is_opt is True
        assert inner is int


class TestIsUnion:
    def test_detects_union(self) -> None:
        is_un, members = is_union(int | str)
        assert is_un is True
        assert set(members) == {int, str}


class TestIsList:
    def test_detects_list_with_type(self) -> None:
        is_lst, elem = is_list(list[int])
        assert is_lst is True
        assert elem is int


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
