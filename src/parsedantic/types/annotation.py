# src/parsedantic/types/annotation.py
from __future__ import annotations

from typing import Annotated, TypeVar

from .metadata import ParsedMetadata

T = TypeVar("T")


def Parsed(value_type: type[T], parser: "Parser[T]") -> type[T]:  # type: ignore[name-defined]
    """Type annotation that associates a parser with a type.

    Returns a typing.Annotated type that carries ParsedMetadata in its metadata.
    """
    return Annotated[value_type, ParsedMetadata(parser)]
