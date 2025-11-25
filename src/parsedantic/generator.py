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
from typing import Any, Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING, Union, get_args, get_origin

import logging

from parsy import Parser, seq, success
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)

from .parsers import float_num, integer, pattern, whitespace

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .models import ParsableModel


def is_optional_type(field_type: Any) -> Tuple[bool, Any | None]:
    """Detect ``Optional[T]`` / ``T | None`` annotations.

    Returns a ``(is_optional, inner_type)`` pair where ``inner_type`` is the
    non-``None`` member for recognised optional types.
    """
    origin = get_origin(field_type)
    if origin not in (Union, UnionType):
        return False, None

    args = get_args(field_type)
    non_none_args = [arg for arg in args if arg is not NoneType]
    none_count = len(args) - len(non_none_args)

    if none_count == 1 and len(non_none_args) == 1:
        return True, non_none_args[0]

    return False, None


def extract_optional_inner_type(field_type: Any) -> Any:
    """Return the inner ``T`` from ``Optional[T]`` / ``T | None``.

    Raises ``TypeError`` if *field_type* is not recognised as optional.
    """
    is_opt, inner = is_optional_type(field_type)
    if not is_opt or inner is None:
        raise TypeError(f"{field_type!r} is not an Optional type")
    return inner


def generate_field_parser(field_type: Any, field_info: FieldInfo) -> Parser[Any]:
    """Generate a parsy :class:`Parser` for a single field.

    Currently this supports a small subset of Python types:

    * ``str`` -> non-whitespace token (``pattern(r"\\S+")``)
    * ``int`` -> integer parser (including negatives)
    * ``float`` -> floating point parser
    * ``Optional[T]`` / ``T | None`` -> delegated to inner ``T``

    Args:
        field_type: The annotation associated with the field.
        field_info: The Pydantic :class:`FieldInfo` for the field. Unused for
            now but kept for future steps where ``ParseField`` metadata will
            influence parser generation.

    Returns:
        A parsy :class:`Parser` that yields the parsed value.

    Raises:
        NotImplementedError: If the type is not yet supported by the
            type-driven machinery.
    """
    # Optional types delegate to their inner annotation. Optional behaviour
    # such as strict/lenient handling is decided at model-parser level.
    is_opt, inner = is_optional_type(field_type)
    if is_opt and inner is not None:
        field_type = inner

    origin = get_origin(field_type) or field_type

    if origin is str:
        return pattern(r"\S+")  # single non-whitespace token
    if origin is int:
        return integer()
    if origin is float:
        return float_num()

    raise NotImplementedError(
        f"Automatic parser generation not implemented for type {field_type!r}"
    )


def _get_field_separator(model_class: type["ParsableModel"]) -> Parser[Any]:
    """Return the parser to use between successive fields.

    Behaviour:

    * If the model defines ``ParseConfig.field_separator``, use that parser.
    * Otherwise default to consuming one-or-more whitespace characters.
    """
    config = getattr(model_class, "ParseConfig", None)
    separator: Parser[Any] | None = None
    if config is not None:
        separator = getattr(config, "field_separator", None)

    if separator is None:
        # Default separator: one-or-more whitespace characters.
        separator = whitespace()

    return separator


def _get_strict_optional(model_class: type["ParsableModel"]) -> bool:
    """Return the ``strict_optional`` flag for *model_class*.

    Defaults to ``True`` when the model does not define an explicit setting.
    """
    config = getattr(model_class, "ParseConfig", None)
    if config is None:
        return True
    return getattr(config, "strict_optional", True)


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[Dict[str, Any]]:
    """Construct a parser that produces a mapping of field values.

    The resulting parser yields a :class:`dict` mapping field names to
    parsed values. :class:`ParsableModel.parse` feeds this mapping into
    ``model_validate`` to obtain a fully validated model instance.

    Field parsers are generated in declaration order using
    :func:`generate_field_parser`. A separator parser is inserted between
    successive fields. Models may override the separator via
    ``ParseConfig.field_separator``. Optional fields honour the
    ``strict_optional`` flag on the model's :class:`ParseConfig`:
    in lenient mode (``False``) optional fields may be omitted or, when they
    are the last fields, consume invalid values and yield ``None``.
    """
    logger.debug("Building model parser for %s", model_class.__name__)

    # Pydantic guarantees ``model_fields`` preserves definition order.
    field_items: Sequence[Tuple[str, FieldInfo]] = tuple(
        model_class.model_fields.items()
    )

    if not field_items:
        # Model with no fields – always succeeds and yields an empty mapping.
        return success({})

    separator = _get_field_separator(model_class)
    strict_optional = _get_strict_optional(model_class)

    # Cache parsers per distinct *base* type within this model.
    type_parser_cache: Dict[Any, Parser[Any]] = {}

    field_names: List[str] = []
    base_parsers: List[Parser[Any]] = []
    optional_kinds: List[str] = []  # "none", "strict", "lenient"

    for name, field_info in field_items:
        field_type = field_info.annotation
        is_opt, inner = is_optional_type(field_type)
        if is_opt and inner is not None:
            base_type = inner
            opt_kind = "lenient" if not strict_optional else "strict"
        else:
            base_type = field_type
            opt_kind = "none"

        if base_type in type_parser_cache:
            parser = type_parser_cache[base_type]
        else:
            parser = generate_field_parser(base_type, field_info)
            type_parser_cache[base_type] = parser

        field_names.append(name)
        base_parsers.append(parser)
        optional_kinds.append(opt_kind)

    # For lenient optional fields that come after the first, we re-use a common
    # "garbage" parser that consumes a single non-whitespace token and yields
    # ``None``. This is used when the inner parser cannot parse the token.
    garbage_token = pattern(r"\S+").result(None)

    combined_parsers: List[Parser[Any]] = []

    first_parser = base_parsers[0]
    if optional_kinds[0] == "lenient":
        # For an optional first field we allow it to be absent; if present but
        # invalid the underlying parser failure will still surface.
        first_parser = first_parser.optional()
    combined_parsers.append(first_parser)

    # Remaining fields are preceded by the separator.
    for index in range(1, len(base_parsers)):
        parser = base_parsers[index]
        opt_kind = optional_kinds[index]

        if opt_kind == "lenient":
            body = parser | garbage_token
            combined = separator.then(body).optional()
        else:
            combined = separator.then(parser)

        combined_parsers.append(combined)

    sequence_parser: Parser[Tuple[Any, ...]] = seq(
        *combined_parsers
    )  # type: ignore[arg-type]

    def to_mapping(values: Iterable[Any]) -> Dict[str, Any]:
        return dict(zip(field_names, values))

    return sequence_parser.map(to_mapping)
