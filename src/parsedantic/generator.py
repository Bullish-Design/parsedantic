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
from typing import Any, Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING, Union, Literal, get_args, get_origin

import logging

from parsy import Parser, seq, success
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)

from .parsers import float_num, integer, literal, pattern, whitespace
from .fields import get_parsefield_metadata


if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .models import ParsableModel


def is_parsable_model(field_type: Any) -> bool:
    """Return ``True`` if *field_type* is a :class:`ParsableModel` subclass.

    The check is intentionally defensive so that it behaves sensibly when
    presented with non-class annotations such as ``list[int]`` or ``Union``.
    The ``ParsableModel`` import is local to avoid import-time cycles between
    :mod:`parsedantic.models` and :mod:`parsedantic.generator`.
    """
    try:
        from .models import ParsableModel  # local import to avoid circular import
    except Exception:  # pragma: no cover - extremely defensive
        return False

    if not isinstance(field_type, type):
        return False

    try:
        return issubclass(field_type, ParsableModel)
    except TypeError:
        return False


def is_optional_type(field_type: Any) -> Tuple[bool, Any | None]:
    """Detect ``Optional[T]`` / ``T | None`` annotations.

    Returns a ``(is_optional, inner_type)`` pair where ``inner_type`` is the
    non-``None`` member (or members) for recognised optional types.

    Any ``Union`` that includes ``None`` is treated as an optional of the
    remaining members. For example ``int | str | None`` is considered
    ``Optional[int | str]``.
    """
    origin = get_origin(field_type)
    if origin not in (Union, UnionType):
        return False, None

    args = get_args(field_type)
    non_none_args = [arg for arg in args if arg is not NoneType]
    none_count = len(args) - len(non_none_args)

    if none_count >= 1 and non_none_args:
        if len(non_none_args) == 1:
            return True, non_none_args[0]
        # Rebuild a Union of the non-None members so that later logic can
        # continue to treat the inner type as a normal Union.
        return True, Union[tuple(non_none_args)]

    return False, None

def is_list_type(field_type: Any) -> Tuple[bool, Any | None]:
    """Detect ``list[T]`` style annotations.

    Returns a ``(is_list, element_type)`` pair where ``element_type`` is the
    inner ``T`` for parameterised lists, or ``None`` for bare ``list`` which
    is considered an error by :func:`generate_field_parser`.
    """
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
    """Detect ``Union[A, B]`` / ``A | B`` annotations (excluding ``None``).

    ``None`` members are excluded because they are handled by
    :func:`is_optional_type`. The returned tuple contains only the non-``None``
    member types in declaration order.
    """
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
) -> Parser[Any]:
    """Generate a parsy :class:`Parser` for a single field.

    Currently this supports a small subset of Python types:

    * ``str`` -> non-whitespace token (``pattern(r"\S+")``)
    * ``int`` -> integer parser (including negatives)
    * ``float`` -> floating point parser
    * ``list[T]`` -> parser for repeated ``T`` values
    * ``Optional[T]`` / ``T | None`` -> delegated to inner ``T``
    * ``Union[A, B]`` / ``A | B`` -> ordered alternatives
    * ``Literal[... ]`` -> string literal values

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
        TypeError: For malformed list types (e.g. bare ``list``) or invalid
            ParseField configuration.
    """
    metadata = get_parsefield_metadata(field_info)

    # Validate ``sep_by`` usage early so we give a clear error message when it
    # is applied to non-list fields.
    is_list, element_type = is_list_type(field_type)
    if (
        metadata is not None
        and metadata.sep_by is not None
        and not is_list
        and not _ignore_sep_by
    ):
        raise TypeError("ParseField(sep_by=...) requires a list[...] field")

    # Lists are handled first so that ``list[Optional[T]]`` is treated as a
    # collection of optional values rather than an optional list.
    if is_list:
        if element_type is None:
            raise TypeError("List fields must specify an element type, e.g. list[int]")

        # Determine the element parser. Explicit ParseField configuration takes
        # precedence over type-driven generation.
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
                )
        else:
            element_parser = generate_field_parser(
                element_type,
                field_info,
                _ignore_sep_by=True,
            )

        # When ``sep_by`` is supplied we build a separated-list parser. When
        # called with ``_ignore_sep_by`` the caller is responsible for adding
        # any list-level behaviour.
        if metadata is not None and metadata.sep_by is not None and not _ignore_sep_by:
            return element_parser.sep_by(metadata.sep_by)

        # Default list behaviour: whitespace-separated elements.
        return element_parser.sep_by(whitespace())

    # At this point the field is not a list. Explicit ParseField configuration
    # can still override the type-driven logic.
    if metadata is not None:
        if metadata.parser is not None:
            return metadata.parser
        if metadata.pattern is not None:
            return pattern(metadata.pattern)

    # Nested ``ParsableModel`` fields compose by delegating to the nested
    # model's own parser. The nested parser typically yields a ``dict`` of
    # field values which we feed back through ``model_validate`` to obtain a
    # fully validated instance of the nested model.
    if is_parsable_model(field_type):
        nested_model_type = field_type

        def _to_nested_model(value: Any) -> Any:
            # If the nested parser already produced a model instance we simply
            # return it; otherwise we validate the parsed mapping.
            if isinstance(value, nested_model_type):
                return value
            return nested_model_type.model_validate(value)

        nested_parser: Parser[Any] = nested_model_type._get_parser()
        return nested_parser.map(_to_nested_model)

    # Optional types delegate to their inner annotation. Optional behaviour
    # such as strict/lenient handling is decided at model-parser level.
    is_opt, inner = is_optional_type(field_type)
    if is_opt and inner is not None:
        field_type = inner

    # Union types (including optional unions whose inner type is a Union) are
    # handled by generating parsers for each member and combining them using
    # parsy's ``|`` operator. Order is significant: the first parser that
    # succeeds without consuming input on failure wins.
    is_union, members = is_union_type(field_type)
    if is_union:
        if not members:
            raise TypeError("Union types must specify at least one non-None member")
        parsers: List[Parser[Any]] = [
            generate_field_parser(member, field_info, _ignore_sep_by=_ignore_sep_by)
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