# src/parsedantic/inference/advanced.py
from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from ..core.parser import Parser
from ..primitives import literal


def is_literal(annotation: Any) -> tuple[bool, tuple]:
    """Return (True, values) if annotation is a Literal[..., ...]."""
    origin = get_origin(annotation)
    if origin is Literal:
        return True, get_args(annotation)
    return False, ()


def is_parsable_model(annotation: Any) -> bool:
    """Return True if annotation is a ParsableModel subclass."""
    from ..model import ParsableModel  # local import to avoid import cycles

    if not isinstance(annotation, type):
        return False

    try:
        return issubclass(annotation, ParsableModel)
    except TypeError:
        # Non-class annotations may reach here under some typing constructs
        return False


def infer_parser(annotation: Any) -> Parser | None:
    """Infer parser with Literal and nested ParsableModel support.

    Falls back to container-level inference for all other types.
    """
    # Literal[...] support (currently string values only)
    is_lit, values = is_literal(annotation)
    if is_lit:
        if not values:
            raise TypeError("Literal[...] must specify at least one value")

        if not all(isinstance(value, str) for value in values):
            raise TypeError("Literal types currently supported only for string values")

        first, *rest = values
        lit_parser: Parser[str] = literal(first)
        for value in rest:
            lit_parser = lit_parser | literal(value)
        return lit_parser

    # Nested ParsableModel support
    if is_parsable_model(annotation):
        from ..model.parser_builder import build_model_parser

        model_class = annotation

        nested_dict_parser = build_model_parser(model_class)

        def to_model(data: dict) -> Any:
            return model_class.model_validate(data)

        def format_nested(model_instance: Any) -> str:
            return model_instance.to_text()

        return Parser(
            nested_dict_parser._parser.map(to_model),
            formatter=format_nested,
        )

    # Fallback: container + basic inference
    from .container import infer_parser as infer_container

    return infer_container(annotation)
