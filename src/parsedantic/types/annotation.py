# src/parsedantic/types/annotation.py
from __future__ import annotations

from typing import Annotated, TypeVar, Any

from .metadata import ParsedMetadata

T = TypeVar("T")


class _ParsedOp:
    """Factory object for creating Parsed annotations.

    Supports both function-style and subscription-style usage:

        Parsed(int, integer())
        Parsed[str, word()]
    """

    def __call__(self, value_type: type[T], parser: "Parser[T]") -> type[T]:  # type: ignore[name-defined]
        return Annotated[value_type, ParsedMetadata(parser)]

    def __getitem__(self, params: Any) -> Any:
        # Allow both Parsed[T, parser] and Parsed[(T, parser)]
        if not isinstance(params, tuple) or len(params) != 2:
            raise TypeError("Parsed[...] expects exactly two arguments: (value_type, parser)")
        value_type, parser = params
        return Annotated[value_type, ParsedMetadata(parser)]


Parsed = _ParsedOp()
