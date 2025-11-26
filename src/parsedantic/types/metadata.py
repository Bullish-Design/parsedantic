# src/parsedantic/types/metadata.py
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin

if TYPE_CHECKING:  # pragma: no cover
    from ..core.parser import Parser


class ParsedMetadata:
    """Metadata attached to Parsed annotations."""

    def __init__(self, parser: "Parser"):
        self.parser = parser

    def __repr__(self) -> str:
        return f"ParsedMetadata({self.parser})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParsedMetadata):
            return False
        # Identity comparison is intentional: we care about the exact parser object
        return self.parser is other.parser


def extract_parser(annotation: Any) -> "Parser | None":
    """Extract Parser from Parsed[T, parser] annotation.

    Returns None when annotation is not an Annotated carrying ParsedMetadata.
    """
    origin = get_origin(annotation)

    if origin is not Annotated:
        return None

    args = get_args(annotation)
    if len(args) < 2:
        return None

    for metadata in args[1:]:
        if isinstance(metadata, ParsedMetadata):
            return metadata.parser

    return None


def get_value_type(annotation: Any) -> type:
    """Extract value type T from Parsed[T, parser].

    For plain (non-Annotated) annotations, the annotation itself is returned.
    """
    origin = get_origin(annotation)

    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return args[0]

    return annotation
