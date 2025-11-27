# src/parsedantic/inference/inference.py
from __future__ import annotations

from types import NoneType, UnionType
from typing import Any, List, Literal, Union, get_args, get_origin

from ..core.parser import Parser
from ..primitives import float_num, integer, literal, string_of, whitespace
from ..types import extract_parser


def get_parser_for_field(annotation: Any) -> Parser | None:
    """Get parser: explicit Parsed[] has priority, then inference."""
    explicit = extract_parser(annotation)
    return explicit if explicit is not None else infer_parser(annotation)


def infer_parser(annotation: Any) -> Parser | None:
    """Infer parser from type annotation."""
    # Literal
    if _is_literal(annotation):
        return _build_literal_parser(annotation)

    # ParsableModel (nested)
    if _is_parsable_model(annotation):
        return _build_model_parser(annotation)

    # Optional
    if _is_optional(annotation):
        return _build_optional_parser(annotation)

    # Union
    if _is_union(annotation):
        return _build_union_parser(annotation)

    # list
    if _is_list(annotation):
        return _build_list_parser(annotation)

    # Basic types
    if annotation is int:
        return integer()
    if annotation is float:
        return float_num()
    if annotation is str:
        return string_of()

    return None


# Type checkers (return bool for internal use)
def _is_literal(annotation: Any) -> bool:
    return get_origin(annotation) is Literal


# def _is_parsable_model(annotation: Any) -> bool:
#     """Duck typing to avoid circular import."""
#     return (
#         isinstance(annotation, type) and
#         hasattr(annotation, 'from_text') and
#         hasattr(annotation, 'to_text') and
#         hasattr(annotation, 'model_fields')
#     )


def _is_parsable_model(annotation: Any) -> bool:
    """Check if ParsableModel using only Pydantic's model_fields."""
    if not isinstance(annotation, type):
        return False

    # Only check model_fields - all Pydantic models have this
    # But ParsableModel adds from_text, so check that too
    has_fields = hasattr(annotation, "model_fields")
    has_from_text = hasattr(annotation, "from_text")

    # Debug: uncomment to see what's happening
    # print(f"Checking {annotation}: model_fields={has_fields}, from_text={has_from_text}")

    return has_fields and has_from_text


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return False
    args = get_args(annotation)
    non_none = [arg for arg in args if arg is not NoneType]
    return len(args) - len(non_none) >= 1 and len(non_none) >= 1


def _is_union(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return False
    members = [arg for arg in get_args(annotation) if arg is not NoneType]
    return len(members) > 1


def _is_list(annotation: Any) -> bool:
    origin = get_origin(annotation)
    return origin is list or origin is List or annotation is list or annotation is List


# Parser builders
def _build_literal_parser(annotation: Any) -> Parser:
    values = get_args(annotation)
    if not values:
        raise TypeError("Literal[...] must specify at least one value")
    if not all(isinstance(v, str) for v in values):
        raise TypeError("Literal types currently only support string values")

    result = literal(values[0])
    for value in values[1:]:
        result = result | literal(value)
    return result


# def _build_model_parser(annotation: Any) -> Parser:
#     from ..model.parser_builder import build_model_parser

#     nested_parser = build_model_parser(annotation)

#     def to_model(data: dict) -> Any:
#         return annotation.model_validate(data)

#     def format_model(instance: Any) -> str:
#         return instance.to_text()

#     return Parser(
#         nested_parser._parser.map(to_model),
#         formatter=format_model,
#     )

def _build_model_parser(annotation: Any) -> Parser:
    """Build a parser for a nested ParsableModel.

    This now goes through the model's TextCodec directly instead of the
    deprecated ``build_model_parser`` helper, which avoids emitting the
    deprecation warning used for backwards compatibility.
    """
    # Prefer a cached codec if the model exposes the helper used by ParsableModel.
    get_codec = getattr(annotation, "_get_codec", None)
    if callable(get_codec):
        codec = get_codec()  # type: ignore[misc]
    else:
        # Fallback for non-ParsableModel-like types that might still reach here.
        from ..codec import TextCodec  # local import to avoid import cycles

        codec = TextCodec(annotation)  # type: ignore[arg-type]

    nested_parser = codec.combined_parser

    def to_model(data: dict) -> Any:
        return annotation.model_validate(data)

    def format_model(instance: Any) -> str:
        return instance.to_text()

    return Parser(
        nested_parser._parser.map(to_model),
        formatter=format_model,
    )

def _build_optional_parser(annotation: Any) -> Parser | None:
    args = get_args(annotation)
    non_none = [arg for arg in args if arg is not NoneType]
    inner = non_none[0] if len(non_none) == 1 else Union[tuple(non_none)]
    inner_parser = infer_parser(inner)
    return inner_parser.optional() if inner_parser else None


def _build_union_parser(annotation: Any) -> Parser | None:
    members = [arg for arg in get_args(annotation) if arg is not NoneType]
    parsers = [infer_parser(m) for m in members]
    if not all(parsers):
        return None
    combined = parsers[0]
    for p in parsers[1:]:
        combined = combined | p
    return combined


def _build_list_parser(annotation: Any) -> Parser:
    args = get_args(annotation)
    element_type = args[0] if args else None
    if element_type is None:
        raise TypeError("list fields must specify element type, e.g. list[int]")
    element_parser = infer_parser(element_type)
    if not element_parser:
        raise TypeError(f"Cannot infer parser for list element type {element_type}")
    return element_parser.sep_by(whitespace())

