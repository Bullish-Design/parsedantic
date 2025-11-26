# src/parsedantic/__init__.py
from __future__ import annotations

from .core import Parser
from .primitives import (
    any_char,
    digit,
    float_num,
    integer,
    letter,
    literal,
    pattern,
    string_of,
    whitespace,
    word,
)

__version__ = "2.0.0"

__all__ = [
    "Parser",
    "literal",
    "pattern",
    "string_of",
    "whitespace",
    "word",
    "integer",
    "float_num",
    "any_char",
    "letter",
    "digit",
]
