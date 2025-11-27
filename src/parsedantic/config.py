# src/parsedantic/config.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .core.parser import Parser
from .primitives import whitespace

if TYPE_CHECKING:
    from .model import ParsableModel


def get_field_separator(model_class: type["ParsableModel"]) -> Parser:
    """Get field separator parser from model_config.

    The separator is looked up from ``model_config['parse_separator']`` and can be:

    * a :class:`Parser` instance - used directly
    * a string - wrapped in :func:`literal` to match exactly
    * missing - defaults to :func:`whitespace`

    Any other type raises :class:`TypeError`.
    """
    config: Any = getattr(model_class, "model_config", {})

    separator = None
    if isinstance(config, dict):
        separator = config.get("parse_separator")

    if separator is not None:
        if isinstance(separator, Parser):
            return separator
        if isinstance(separator, str):
            from .primitives import literal

            return literal(separator)
        raise TypeError(f"parse_separator must be Parser or str, got {type(separator)}")

    return whitespace()
