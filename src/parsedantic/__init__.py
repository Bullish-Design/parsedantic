# src/parsedantic/__init__.py
from __future__ import annotations

"""Parsedantic package root.

This module defines the public API surface exposed to users. At Step 4 the
surface is intentionally small: it includes the core :class:`ParsableModel`
base class, the :class:`ParseError` type used for parse failures, and the
primitive parser builder functions.
"""

from .errors import ParseError
from .models import ParsableModel
from .parsers import (
    any_char,
    float_num,
    integer,
    literal,
    pattern,
    whitespace,
    word,
)

__all__: list[str] = [
    "ParsableModel",
    "ParseError",
    "literal",
    "pattern",
    "integer",
    "float_num",
    "word",
    "whitespace",
    "any_char",
]
