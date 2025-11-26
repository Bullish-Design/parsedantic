# src/parsedantic/inference/container.py
from __future__ import annotations

from types import NoneType, UnionType
from typing import Any, List, Union, get_args, get_origin

from ..core.parser import Parser
from ..primitives import whitespace


def is_optional(annotation: Any) -> tuple[bool, Any]:
    """Check if Optional[T] or T | None."""
    origin = get_origin(annotation)

    if origin not in (Union, UnionType):
        return False, None

    args = get_args(annotation)
    non_none_args = [arg for arg in args if arg is not NoneType]
    none_count = len(args) - len(non_none_args)

    if none_count >= 1 and non_none_args:
        if len(non_none_args) == 1:
            return True, non_none_args[0]
        return True, Union[tuple(non_none_args)]

    return False, None


def is_union(annotation: Any) -> tuple[bool, tuple]:
    """Check if Union[A, B] (excluding None)."""
    origin = get_origin(annotation)

    if origin not in (Union, UnionType):
        return False, ()

    members = tuple(arg for arg in get_args(annotation) if arg is not NoneType)

    if len(members) > 1:
        return True, members

    return False, ()


def is_list(annotation: Any) -> tuple[bool, Any]:
    """Check if list[T]."""
    origin = get_origin(annotation)

    if origin is list or origin is List:
        args = get_args(annotation)
        if args:
            return True, args[0]
        return True, None

    if annotation is list or annotation is List:
        return True, None

    return False, None


def infer_parser(annotation: Any) -> Parser | None:
    """Infer parser with container support."""
    from .basic import infer_parser as infer_basic

    # Check Optional[T]
    is_opt, inner = is_optional(annotation)
    if is_opt:
        inner_parser = infer_parser(inner)
        if inner_parser:
            return inner_parser.optional()
        return None

    # Check Union[A, B]
    is_un, members = is_union(annotation)
    if is_un:
        parsers = [infer_parser(m) for m in members]

        if all(p is not None for p in parsers):
            combined = parsers[0]
            for p in parsers[1:]:
                combined = combined | p
            return combined
        return None

    # Check list[T]
    is_lst, element_type = is_list(annotation)
    if is_lst:
        if element_type is None:
            raise TypeError("list fields must specify element type, e.g. list[int]")

        element_parser = infer_parser(element_type)
        if element_parser:
            return element_parser.sep_by(whitespace())
        return None

    return infer_basic(annotation)
