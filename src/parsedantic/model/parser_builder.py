# src/parsedantic/model/parser_builder.py
from __future__ import annotations

from typing import Any, get_type_hints

import parsy

from ..core.parser import Parser
from ..inference import get_parser_for_field
from ..primitives import whitespace


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[dict[str, Any]]:
    """Build parser from model schema."""
    try:
        hints = get_type_hints(model_class)
    except NameError:
        # Forward refs unresolved - use empty dict, will fall back to field_info
        hints = {}
    except Exception:
        hints = {}

    fields = model_class.model_fields

    if not fields:
        return Parser(parsy.success({}))

    field_parsers: list[tuple[str, Parser]] = []

    for field_name, field_info in fields.items():
        # Get annotation from hints, but use field_info.annotation if:
        # 1. Not in hints, or
        # 2. Is a string (unresolved forward ref)
        annotation = hints.get(field_name)
        if annotation is None or isinstance(annotation, str):
            annotation = field_info.annotation
        
        parser = get_parser_for_field(annotation)

        if parser is None:
            raise TypeError(
                f"Cannot generate parser for field '{field_name}' with type {annotation}. "
                f"Use Parsed[T, parser] to specify explicit parser."
            )

        field_parsers.append((field_name, parser))

    return _combine_field_parsers(field_parsers)


def _combine_field_parsers(
    field_parsers: list[tuple[str, Parser]],
) -> Parser[dict[str, Any]]:
    """Combine field parsers with whitespace separation."""
    if not field_parsers:
        return Parser(parsy.success({}))

    parsers = [field_parsers[0][1]._parser]
    for _, field_parser in field_parsers[1:]:
        parsers.append(whitespace()._parser)
        parsers.append(field_parser._parser)

    parsy_parser = parsy.seq(*parsers)

    def to_dict(values: tuple) -> dict[str, Any]:
        field_values = [values[i] for i in range(0, len(values), 2)]
        return dict(zip([name for name, _ in field_parsers], field_values))

    return Parser(parsy_parser.map(to_dict))