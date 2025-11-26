# src/parsedantic/inference/inference.py
from __future__ import annotations

from types import NoneType, UnionType
from typing import TYPE_CHECKING, Any, List, Literal, Union, get_args, get_origin

from ..core.parser import Parser
from ..primitives import float_num, integer, string_of, whitespace
from ..types import extract_parser

if TYPE_CHECKING:
    from ..model.base import ParsableModel


def get_parser_for_field(annotation: Any) -> Parser | None:
    """Get parser for field - checks explicit Parsed[] first, then infers.

    Priority:
    1. Explicit Parsed[T, parser] annotation
    2. Inferred from type
    """
    explicit = extract_parser(annotation)
    if explicit is not None:
        return explicit

    return infer_parser(annotation)


def infer_parser(annotation: Any) -> Parser | None:
    """Infer parser from type annotation.

    Handles all supported types in priority order:
    - Literal["value", ...]
    - ParsableModel (nested models)
    - Optional[T]
    - Union[A, B, ...]
    - list[T]
    - Basic types: int, str, float
    """
    # Literal types
    is_lit, values = _is_literal(annotation)
    if is_lit:
        if not values:
            raise TypeError("Literal[...] must specify at least one value")
        if not all(isinstance(v, str) for v in values):
            raise TypeError("Literal types currently only support string values")

        from ..primitives import literal

        result = literal(values[0])
        for value in values[1:]:
            result = result | literal(value)
        return result

    # ParsableModel (nested models)
    if _is_parsable_model(annotation):
        from ..model.parser_builder import build_model_parser

        nested_parser = build_model_parser(annotation)

        def to_model(data: dict) -> Any:
            return annotation.model_validate(data)

        def format_model(instance: Any) -> str:
            return instance.to_text()

        return Parser(
            nested_parser._parser.map(to_model),
            formatter=format_model,
        )

    # Optional[T]
    is_opt, inner = _is_optional(annotation)
    if is_opt:
        inner_parser = infer_parser(inner)
        if inner_parser:
            return inner_parser.optional()
        return None

    # Union[A, B, ...]
    is_union, members = _is_union(annotation)
    if is_union:
        parsers = [infer_parser(m) for m in members]
        if all(p is not None for p in parsers):
            combined = parsers[0]
            for p in parsers[1:]:
                combined = combined | p
            return combined
        return None

    # list[T]
    is_list, element_type = _is_list(annotation)
    if is_list:
        if element_type is None:
            raise TypeError("list fields must specify element type, e.g. list[int]")
        element_parser = infer_parser(element_type)
        if element_parser:
            return element_parser.sep_by(whitespace())
        return None

    # Basic types
    if annotation is int:
        return integer()
    if annotation is float:
        return float_num()
    if annotation is str:
        return string_of()

    return None


def _is_literal(annotation: Any) -> tuple[bool, tuple]:
    """Check if annotation is Literal[...]."""
    origin = get_origin(annotation)
    if origin is Literal:
        return True, get_args(annotation)
    return False, ()


def _is_parsable_model(annotation: Any) -> bool:
    """Check if annotation is a ParsableModel subclass."""
    if not isinstance(annotation, type):
        return False

    try:
        from ..model.base import ParsableModel

        return issubclass(annotation, ParsableModel)
    except (TypeError, ImportError):
        return False


def _is_optional(annotation: Any) -> tuple[bool, Any]:
    """Check if annotation is Optional[T] or T | None."""
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return False, None

    args = get_args(annotation)
    non_none = [arg for arg in args if arg is not NoneType]
    none_count = len(args) - len(non_none)

    if none_count >= 1 and non_none:
        if len(non_none) == 1:
            return True, non_none[0]
        return True, Union[tuple(non_none)]

    return False, None


def _is_union(annotation: Any) -> tuple[bool, tuple]:
    """Check if annotation is Union[A, B, ...] (excluding None)."""
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return False, ()

    members = tuple(arg for arg in get_args(annotation) if arg is not NoneType)
    if len(members) > 1:
        return True, members

    return False, ()


def _is_list(annotation: Any) -> tuple[bool, Any]:
    """Check if annotation is list[T]."""
    origin = get_origin(annotation)

    if origin is list or origin is List:
        args = get_args(annotation)
        return True, (args[0] if args else None)

    if annotation is list or annotation is List:
        return True, None

    return False, None
