# src/parsedantic/__init__.py
from __future__ import annotations

from .core import Parser
from .primitives import (
    any_char,
    digit,
    eof,
    fail,
    float_num,
    index,
    integer,
    letter,
    line_info,
    literal,
    pattern,
    peek,
    string_of,
    success,
    whitespace,
    word,
)

from .types import Parsed


__version__ = "2.0.0"

__all__ = [
    "Parser",
    "Parsed",
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
    "success",
    "fail",
    "eof",
    "peek",
    "index",
    "line_info",
]

