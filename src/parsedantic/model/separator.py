# src/parsedantic/model/separator.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .base import ParsableModel


def get_separator_string(model_class: type["ParsableModel"]) -> str:
    """Extract separator as a string from model_config.

    Why: Both parsing and serialization need the separator as a string.
    Parser-based separators are not yet supported for serialization.

    Args:
        model_class: The ParsableModel class to inspect

    Returns:
        Separator string (defaults to " " if not configured)
    """
    config: Any = getattr(model_class, "model_config", {})

    if not isinstance(config, dict):
        return " "

    sep_config = config.get("parse_separator")

    if sep_config is None:
        return " "

    # String separators work directly
    if isinstance(sep_config, str):
        return sep_config

    # Parser-based separators: use space as fallback
    # TODO: Extract string from Parser in future enhancement
    return " "
