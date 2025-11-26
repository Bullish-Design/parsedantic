# src/parsedantic/__init__.py
from __future__ import annotations

from .core import Parser
from .errors import ParseError
from .model import ParsableModel
from .primitives import (
    any_char,
    char_from,
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
    string_from,
    string_of,
    success,
    test_char,
    test_item,
    whitespace,
    word,
)
from .types import Parsed

__version__ = "2.0.0"

__all__ = [
    "Parser",
    "Parsed",
    "ParseError",
    "ParsableModel",
    "literal",
    "pattern",
    "string_of",
    "whitespace",
    "word",
    "integer",
    "float_num",
    "any_char",
    "char_from",
    "string_from",
    "test_char",
    "test_item",
    "letter",
    "digit",
    "success",
    "fail",
    "eof",
    "peek",
    "index",
    "line_info",
]