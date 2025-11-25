# src/parsedantic/fields.py
from __future__ import annotations

"""Field utilities for Parsedantic.

Step 10 introduces :func:`ParseField`, a thin wrapper around Pydantic's
:func:`Field` that can carry parser-specific metadata. Later steps extend
this with additional behaviours such as regex patterns and separated lists.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from parsy import Parser
from pydantic import Field as PydanticField
from pydantic.fields import FieldInfo


@dataclass
class ParseFieldMetadata:
    """Metadata attached to a Pydantic field by :func:`ParseField`.

    Only the ``parser`` attribute is used in Step 10; other attributes are
    reserved for later steps and kept here so that the metadata structure
    remains stable across the implementation phases.
    """

    pattern: str | None = None
    parser: Parser[Any] | None = None
    sep_by: Parser[Any] | None = None


def get_parsefield_metadata(field_info: FieldInfo) -> ParseFieldMetadata | None:
    """Return :class:`ParseFieldMetadata` attached to *field_info*, if any.

    The metadata is stored either in the ``metadata`` attribute or in the
    ``json_schema_extra`` mapping of the underlying :class:`FieldInfo` object.
    This helper hides these storage details from the rest of the codebase.
    """
    # First, look through the ``metadata`` attribute if it exists.
    raw: Iterable[Any] | None = getattr(field_info, "metadata", None)
    if raw:
        for item in raw:
            if isinstance(item, ParseFieldMetadata):
                return item

    # For Pydantic v2, extra data supplied to :func:`Field` is stored in
    # ``json_schema_extra``. ParseField uses this to keep its metadata.
    extra = getattr(field_info, "json_schema_extra", None)
    if isinstance(extra, dict):
        candidate = extra.get("parsedantic")
        if isinstance(candidate, ParseFieldMetadata):
            return candidate

        # Support older storage under ``metadata`` for robustness.
        meta_value = extra.get("metadata")
        if isinstance(meta_value, ParseFieldMetadata):
            return meta_value
        if isinstance(meta_value, Iterable):
            for item in meta_value:
                if isinstance(item, ParseFieldMetadata):
                    return item

    return None


def ParseField(
    *args: Any,
    pattern: str | None = None,
    parser: Parser[Any] | None = None,
    sep_by: Parser[Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Return a Pydantic ``Field`` with parser metadata attached.

    The positional and most keyword arguments are passed straight through to
    :func:`pydantic.Field`. Parsedantic-specific arguments are removed and
    encoded into a :class:`ParseFieldMetadata` instance stored in the field's
    ``json_schema_extra`` collection.

    Step 10 only makes use of the ``parser`` argument; ``pattern`` and
    ``sep_by`` are accepted for forward compatibility and become meaningful
    in Step 11.

    Args:
        *args: Positional arguments accepted by :func:`pydantic.Field`.
        pattern: Optional regular expression string used in later steps.
        parser: Explicit parsy :class:`Parser` to use for this field.
        sep_by: Separator parser for list fields in later steps.
        **kwargs: Additional keyword arguments for :func:`pydantic.Field`.

    Returns:
        A configured Pydantic ``FieldInfo`` instance.
    """
    if pattern is not None and parser is not None:
        raise ValueError("ParseField cannot specify both 'pattern' and 'parser'")

    # Preserve any user-specified json_schema_extra while appending ours.
    existing_extra = kwargs.pop("json_schema_extra", None)

    if existing_extra is None:
        extra: dict[str, Any] = {}
    elif isinstance(existing_extra, dict):
        extra = dict(existing_extra)
    else:
        # Normalise non-dict values under a dedicated key so we do not lose
        # information. This situation is unlikely in normal Parsedantic usage.
        extra = {"user_json_schema_extra": existing_extra}

    extra["parsedantic"] = ParseFieldMetadata(
        pattern=pattern,
        parser=parser,
        sep_by=sep_by,
    )
    kwargs["json_schema_extra"] = extra

    return PydanticField(*args, **kwargs)
