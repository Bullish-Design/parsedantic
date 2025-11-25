# src/parsedantic/generator.py
from __future__ import annotations

"""Parser generation utilities for :class:`ParsableModel`.

Step 5 introduces *type-driven* parser generation for simple field types.
This module knows how to turn basic Python type annotations into parsy
``Parser`` objects and how to assemble them into a model-level parser.

At this step we intentionally support only the primitive scalar types
``str``, ``int`` and ``float``. Later steps extend this to Optional, list,
Union and more complex scenarios.
"""

from typing import Any, Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING, get_args, get_origin

from parsy import Parser, seq, success
from pydantic.fields import FieldInfo

from .parsers import float_num, integer, pattern, whitespace

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .models import ParsableModel


def generate_field_parser(field_type: Any, field_info: FieldInfo) -> Parser[Any]:
    """Generate a parsy :class:`Parser` for a single field.

    Currently this supports only a small subset of Python types:

    * ``str`` -> non-whitespace token (``pattern(r"\\S+")``)
    * ``int`` -> integer parser (including negatives)
    * ``float`` -> floating point parser

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

    For Step 5 we keep the behaviour simple:

    * If the model defines ``ParseConfig.field_separator``, use that parser.
    * Otherwise default to consuming one-or-more whitespace characters.
    """
    config = getattr(model_class, "ParseConfig", None)
    separator = None
    if config is not None:
        separator = getattr(config, "field_separator", None)

    if separator is None:
        # Default separator: one-or-more whitespace characters.
        separator = whitespace()

    return separator


def build_model_parser(model_class: type["ParsableModel"]) -> Parser[Dict[str, Any]]:
    """Construct a parser that produces a mapping of field values.

    The resulting parser yields a :class:`dict` mapping field names to parsed
    values. :class:`ParsableModel.parse` feeds this mapping into
    ``model_validate`` to obtain a fully validated model instance.

    Field parsers are generated in declaration order using
    :func:`generate_field_parser`. A separator parser is inserted between
    successive fields. By default this is a whitespace parser, but models may
    override it via ``ParseConfig.field_separator``.
    """
    # Pydantic guarantees ``model_fields`` preserves definition order.
    field_items: Sequence[Tuple[str, FieldInfo]] = tuple(
        model_class.model_fields.items()
    )

    if not field_items:
        # Model with no fields – always succeeds and yields an empty mapping.
        return success({})

    # Build a parser for each field.
    field_names: List[str] = []
    field_parsers: List[Parser[Any]] = []
    for name, field in field_items:
        field_names.append(name)
        field_parsers.append(generate_field_parser(field.annotation, field))

    separator = _get_field_separator(model_class)

    # Interleave a separator between the field parsers. We keep only the field
    # values by sequencing ``separator.then(parser)`` for subsequent fields.
    combined_parsers: List[Parser[Any]] = []
    first, *rest = field_parsers
    combined_parsers.append(first)
    for parser in rest:
        combined_parsers.append(separator.then(parser))

    sequence_parser: Parser[Tuple[Any, ...]] = seq(*combined_parsers)  # type: ignore[arg-type]

    def to_mapping(values: Iterable[Any]) -> Dict[str, Any]:
        return dict(zip(field_names, values))

    return sequence_parser.map(to_mapping)
