# src/parsedantic/model/serializer.py
from __future__ import annotations

from typing import TYPE_CHECKING, get_type_hints

from ..inference import get_parser_for_field

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .base import ParsableModel


def serialize_model(model: "ParsableModel") -> str:
    """Serialize model to text using field parsers."""
    model_cls = type(model)
    try:
        hints = get_type_hints(model_cls)
    except Exception:  # pragma: no cover - fallback for unusual cases
        hints = getattr(model_cls, "__annotations__", {})

    fields = model_cls.model_fields
    parts: list[str] = []

    for field_name, field_info in fields.items():
        annotation = hints.get(field_name, field_info.annotation)
        parser = get_parser_for_field(annotation)

        if parser is None:
            raise TypeError(f"Cannot serialize field '{field_name}' - no parser available")

        value = getattr(model, field_name)
        formatted = parser.format(value)
        parts.append(formatted)

    return " ".join(parts)
