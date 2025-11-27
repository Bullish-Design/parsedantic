# src/parsedantic/model/parser_builder.py
from __future__ import annotations

from typing import TYPE_CHECKING, get_type_hints

import parsy

from ..config import get_field_separator
from ..core.parser import Parser
from ..inference import get_parser_for_field

if TYPE_CHECKING:
    from .base import ParsableModel


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[dict[str, object]]:
    """Build parser from model schema."""
    try:
        hints = get_type_hints(model_class)
    except Exception:
        # hints = getattr(model_class, "__annotations__", {})
        hints = {}

    fields = model_class.model_fields

    if not fields:
        return Parser(parsy.success({}))

    field_parsers: list[tuple[str, Parser]] = []

    for field_name, field_info in fields.items():
        annotation = hints.get(field_name, field_info.annotation)
        parser = get_parser_for_field(annotation)

        if parser is None:
            raise TypeError(
                "Cannot generate parser for field "
                f"'{field_name}' with type {annotation}. "
                "Use Parsed[T, parser] to specify explicit parser."
            )

        if field_info.description:
            parser = parser.desc(field_info.description)

        field_parsers.append((field_name, parser))

    separator = get_field_separator(model_class)
    return _combine_field_parsers(field_parsers, separator)


def _combine_field_parsers(
    field_parsers: list[tuple[str, Parser]],
    separator: Parser,
) -> Parser[dict[str, object]]:
    """Combine field parsers with configured separator."""
    if not field_parsers:
        return Parser(parsy.success({}))

    parsers = [field_parsers[0][1]._parser]
    for _, field_parser in field_parsers[1:]:
        parsers.append(separator._parser)
        parsers.append(field_parser._parser)

    parsy_parser = parsy.seq(*parsers)

    def to_dict(values: tuple) -> dict[str, object]:
        field_values = [values[i] for i in range(0, len(values), 2)]
        names = [name for name, _ in field_parsers]
        return dict(zip(names, field_values))

    return Parser(parsy_parser.map(to_dict))
