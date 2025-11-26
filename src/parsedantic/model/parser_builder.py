# src/parsedantic/model/parser_builder.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_type_hints

import parsy

from ..core.parser import Parser
from ..inference import get_parser_for_field
from ..primitives import whitespace

if TYPE_CHECKING:
    from .base import ParsableModel


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[dict[str, Any]]:
    """Build parser from model schema."""
    try:
        hints = get_type_hints(model_class)
    except NameError as exc:
        # Unresolved forward reference in annotations
        raise TypeError(f"Unresolved forward reference in {model_class.__name__}: {exc}") from exc
    except Exception:
        # Fallback for any other issues resolving type hints
        hints = getattr(model_class, "__annotations__", {})

    fields = model_class.model_fields

    if not fields:
        return Parser(parsy.success({}))

    field_parsers: list[tuple[str, Parser]] = []

    for field_name, field_info in fields.items():
        annotation = hints.get(field_name, field_info.annotation)
        parser = get_parser_for_field(annotation)

        if parser is None:
            raise TypeError(
                f"Cannot generate parser for field '{field_name}' with type {annotation}. "
                f"Use Parsed[T, parser] to specify explicit parser."
            )

        if field_info.description:
            parser = parser.desc(field_info.description)

        field_parsers.append((field_name, parser))

    return _combine_field_parsers(field_parsers)


def _combine_field_parsers(field_parsers: list[tuple[str, Parser]]) -> Parser[dict[str, Any]]:
    """Combine field parsers with whitespace."""
    if not field_parsers:
        return Parser(parsy.success({}))

    # Build parsy-level parser sequence: field1, (ws, fieldN)*
    parsers: list[parsy.Parser] = [field_parsers[0][1]._parser]
    for _, field_parser in field_parsers[1:]:
        parsers.append(whitespace()._parser)
        parsers.append(field_parser._parser)

    parsy_parser = parsy.seq(*parsers)

    def to_dict(values: tuple[object, ...]) -> dict[str, Any]:
        # Field values are at even indices: 0, 2, 4, ...
        field_values = [values[i] for i in range(0, len(values), 2)]
        names = [name for name, _ in field_parsers]
        return dict(zip(names, field_values))

    return Parser(parsy_parser.map(to_dict))
