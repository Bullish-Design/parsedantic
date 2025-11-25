# src/parsedantic/generator.py
from __future__ import annotations

"""Parser generation utilities for :class:`ParsableModel`.

Step 5 introduces *type-driven* parser generation for simple field types.
This module knows how to turn basic Python type annotations into parsy
``Parser`` objects and how to assemble them into a model-level parser.

Step 7 extends this with support for ``Optional[T]`` / ``T | None`` fields,
including configurable strict/lenient handling via ``ParseConfig``.
"""

from types import NoneType, UnionType
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    Union,
    Literal,
    get_args,
    get_origin,
    get_type_hints,
)

import logging
import re

from parsy import Parser, seq, success
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)

from .parsers import float_num, integer, literal, pattern, whitespace
from .fields import get_parsefield_metadata


if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .models import ParsableModel


def _extract_literal_string(parser: Parser[Any]) -> str | None:
    """Extract the literal string from a literal() parser if possible."""
    # Check for the _literal_value attribute we set in parsers.literal()
    return getattr(parser, "_literal_value", None)


def _build_string_parser(separator_chars: str | None = None) -> Parser[str]:
    """Build a string parser that stops at whitespace and optional separator chars."""
    if separator_chars:
        escaped = re.escape(separator_chars)
        return pattern(rf"[^\s{escaped}]+")
    else:
        return pattern(r"\S+")


def is_parsable_model(field_type: Any) -> bool:
    """Return ``True`` if *field_type* is a :class:`ParsableModel` subclass."""
    try:
        from .models import ParsableModel
    except Exception:  # pragma: no cover
        return False

    if not isinstance(field_type, type):
        return False

    try:
        return issubclass(field_type, ParsableModel)
    except TypeError:
        return False


def is_optional_type(field_type: Any) -> Tuple[bool, Any | None]:
    """Detect ``Optional[T]`` / ``T | None`` annotations."""
    origin = get_origin(field_type)
    if origin not in (Union, UnionType):
        return False, None

    args = get_args(field_type)
    non_none_args = [arg for arg in args if arg is not NoneType]
    none_count = len(args) - len(non_none_args)

    if none_count >= 1 and non_none_args:
        if len(non_none_args) == 1:
            return True, non_none_args[0]
        return True, Union[tuple(non_none_args)]

    return False, None


def is_list_type(field_type: Any) -> Tuple[bool, Any | None]:
    """Detect ``list[T]`` style annotations."""
    origin = get_origin(field_type)

    if origin is list or origin is List:
        args = get_args(field_type)
        if not args:
            return True, None
        return True, args[0]

    if field_type is list or field_type is List:
        return True, None

    return False, None


def is_union_type(field_type: Any) -> Tuple[bool, Tuple[Any, ...]]:
    """Detect ``Union[A, B]`` / ``A | B`` annotations (excluding ``None``)."""
    origin = get_origin(field_type)
    if origin not in (Union, UnionType):
        return False, ()

    members = tuple(arg for arg in get_args(field_type) if arg is not NoneType)
    if not members:
        return False, ()

    return True, members


def generate_field_parser(
    field_type: Any,
    field_info: FieldInfo,
    *,
    _ignore_sep_by: bool = False,
    _separator_chars: str | None = None,
) -> Parser[Any]:
    """Generate a parsy :class:`Parser` for a single field.

    Currently this supports a small subset of Python types:

    * ``str`` -> non-whitespace token (pattern(r"\\S+"))
    * ``int`` -> integer parser (including negatives)
    * ``float`` -> floating point parser
    * ``list[T]`` -> parser for repeated ``T`` values
    * ``Optional[T]`` / ``T | None`` -> delegated to inner ``T``
    * ``Union[A, B]`` / ``A | B`` -> ordered alternatives
    * ``Literal[... ]`` -> string literal values

    Args:
        field_type: The annotation associated with the field.
        field_info: The Pydantic :class:`FieldInfo` for the field.
        _ignore_sep_by: Internal flag to disable sep_by handling for recursive calls.
        _separator_chars: Optional string of characters that act as field separators.

    Returns:
        A parsy :class:`Parser` that yields the parsed value.

    Raises:
        NotImplementedError: If the type is not yet supported.
        TypeError: For malformed list types or invalid ParseField configuration.
    """
    metadata = get_parsefield_metadata(field_info)

    # Validate ``sep_by`` usage early
    is_list, element_type = is_list_type(field_type)
    if (
        metadata is not None
        and metadata.sep_by is not None
        and not is_list
        and not _ignore_sep_by
    ):
        raise TypeError("ParseField(sep_by=...) requires a list[...] field")

    # Lists are handled first
    if is_list:
        if element_type is None:
            raise TypeError("List fields must specify an element type, e.g. list[int]")

        # Determine the element parser
        if metadata is not None:
            if metadata.parser is not None:
                element_parser: Parser[Any] = metadata.parser
            elif metadata.pattern is not None:
                element_parser = pattern(metadata.pattern)
            else:
                element_parser = generate_field_parser(
                    element_type,
                    field_info,
                    _ignore_sep_by=True,
                    _separator_chars=_separator_chars,
                )
        else:
            element_parser = generate_field_parser(
                element_type,
                field_info,
                _ignore_sep_by=True,
                _separator_chars=_separator_chars,
            )

        # When ``sep_by`` is supplied we build a separated-list parser
        if metadata is not None and metadata.sep_by is not None and not _ignore_sep_by:
            return element_parser.sep_by(metadata.sep_by)

        # Default list behaviour: whitespace-separated elements
        return element_parser.sep_by(whitespace())

    # At this point the field is not a list. Explicit ParseField configuration
    # can still override the type-driven logic.
    if metadata is not None:
        if metadata.parser is not None:
            return metadata.parser
        if metadata.pattern is not None:
            return pattern(metadata.pattern)

    # Nested ``ParsableModel`` fields compose by delegating to the nested
    # model's own parser.
    if is_parsable_model(field_type):
        nested_model_type = field_type

        def _to_nested_model(value: Any) -> Any:
            if isinstance(value, nested_model_type):
                return value
            return nested_model_type.model_validate(value)

        nested_parser: Parser[Any] = nested_model_type._get_parser()
        return nested_parser.map(_to_nested_model)

    # Optional types delegate to their inner annotation
    is_opt, inner = is_optional_type(field_type)
    if is_opt and inner is not None:
        field_type = inner

    # Union types are handled by generating parsers for each member
    is_union, members = is_union_type(field_type)
    if is_union:
        if not members:
            raise TypeError("Union types must specify at least one non-None member")
        parsers: List[Parser[Any]] = [
            generate_field_parser(
                member,
                field_info,
                _ignore_sep_by=_ignore_sep_by,
                _separator_chars=_separator_chars,
            )
            for member in members
        ]
        combined = parsers[0]
        for alt in parsers[1:]:
            combined = combined | alt
        return combined

    origin = get_origin(field_type) or field_type

    if origin is Literal:
        literal_values = get_args(field_type)
        if not literal_values:
            raise TypeError("Literal[...] must specify at least one value")
        first, *rest = literal_values
        if not isinstance(first, str) or any(not isinstance(v, str) for v in rest):
            raise NotImplementedError(
                "Literal types are currently supported only for string values"
            )
        lit_parser: Parser[str] = literal(first)
        for value in rest:
            lit_parser = lit_parser | literal(value)
        return lit_parser  # type: ignore[return-value]

    if origin is str:
        return _build_string_parser(_separator_chars)
    if origin is int:
        return integer()
    if origin is float:
        return float_num()

    raise NotImplementedError(
        f"Automatic parser generation not implemented for type {field_type!r}"
    )


def _get_field_separator(model_class: type["ParsableModel"]) -> Parser[Any]:
    """Return the parser to use between successive fields."""
    # Only use ParseConfig if defined directly on this class, not inherited
    config = model_class.__dict__.get("ParseConfig", None)
    separator: Parser[Any] | None = None
    if config is not None:
        separator = getattr(config, "field_separator", None)

    if separator is None:
        separator = whitespace()

    return separator


def _get_strict_optional(model_class: type["ParsableModel"]) -> bool:
    """Return the ``strict_optional`` flag for *model_class*."""
    # Only use ParseConfig if defined directly on this class, not inherited
    config = model_class.__dict__.get("ParseConfig", None)
    if config is None:
        return True
    return getattr(config, "strict_optional", True)


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[Dict[str, Any]]:
    """Construct a parser that produces a mapping of field values."""
    logger.debug("Building model parser for %s", model_class.__name__)

    try:
        type_hints = get_type_hints(model_class)
    except NameError as exc:
        raise TypeError(
            f"Unresolved forward reference in annotations for "
            f"{model_class.__name__}: {exc}"
        ) from exc
    except TypeError:
        type_hints = {}

    field_items: Sequence[Tuple[str, FieldInfo]] = tuple(
        model_class.model_fields.items()
    )

    if not field_items:
        return success({})

    separator = _get_field_separator(model_class)
    strict_optional = _get_strict_optional(model_class)

    # Extract separator character(s) if it's a literal parser
    separator_chars = _extract_literal_string(separator)

    # Cache parsers per distinct *base* type within this model
    type_parser_cache: Dict[Any, Parser[Any]] = {}

    field_names: List[str] = []
    base_parsers: List[Parser[Any]] = []
    optional_kinds: List[str] = []  # "none", "strict", "lenient"

    for name, field_info in field_items:
        field_type = type_hints.get(name, field_info.annotation)
        is_opt, inner = is_optional_type(field_type)
        if is_opt and inner is not None:
            base_type = inner
            opt_kind = "lenient" if not strict_optional else "strict"
        else:
            base_type = field_type
            opt_kind = "none"

        # When we have separator chars, we can't safely cache string parsers
        if separator_chars and base_type is str:
            parser = generate_field_parser(
                base_type, field_info, _separator_chars=separator_chars
            )
        elif base_type in type_parser_cache:
            parser = type_parser_cache[base_type]
        else:
            parser = generate_field_parser(
                base_type, field_info, _separator_chars=separator_chars
            )
            # Only cache if not separator-dependent
            if not (separator_chars and base_type is str):
                type_parser_cache[base_type] = parser

        field_names.append(name)
        base_parsers.append(parser)
        optional_kinds.append(opt_kind)

    # For lenient optional fields, garbage token yields None
    garbage_token = pattern(r"\S+").result(None)

    combined_parsers: List[Parser[Any]] = []

    first_parser = base_parsers[0]
    if optional_kinds[0] == "lenient":
        first_parser = first_parser.optional()
    combined_parsers.append(first_parser)

    # Remaining fields are preceded by the separator
    for index in range(1, len(base_parsers)):
        parser = base_parsers[index]
        opt_kind = optional_kinds[index]

        if opt_kind == "lenient":
            body = parser | garbage_token
            combined = separator.then(body).optional()
        else:
            combined = separator.then(parser)

        combined_parsers.append(combined)

    sequence_parser: Parser[Tuple[Any, ...]] = seq(*combined_parsers)  # type: ignore[arg-type]

    def to_mapping(values: Iterable[Any]) -> Dict[str, Any]:
        return dict(zip(field_names, values))

    return sequence_parser.map(to_mapping)

