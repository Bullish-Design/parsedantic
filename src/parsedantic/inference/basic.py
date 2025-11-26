# src/parsedantic/inference/basic.py
from __future__ import annotations

from typing import Any

from ..core.parser import Parser
from ..primitives import float_num, integer, string_of


def infer_parser(annotation: Any) -> Parser | None:
    """Infer parser from basic type annotation."""
    if annotation is int:
        return integer()
    if annotation is float:
        return float_num()
    if annotation is str:
        return string_of()
    return None


def get_parser_for_field(annotation: Any) -> Parser | None:
    """Get parser with priority: Parsed[] > inferred."""
    from ..types import extract_parser

    explicit = extract_parser(annotation)
    if explicit is not None:
        return explicit

    return infer_parser(annotation)
