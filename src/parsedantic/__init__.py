# src/parsedantic/__init__.py
from __future__ import annotations

"""Parsedantic package root.

This module defines the public API surface exposed to users. By Step 13 the
surface includes the core :class:`ParsableModel` base class, the
:class:`ParseError` type used for parse failures, the :class:`ParseField`
helper for per-field parser customisation, configuration helpers, and the
primitive parser builder functions.
"""

from .errors import ParseError
from .models import ParsableModel
from .fields import ParseField
from .config import ParseConfig
from .builder import parser_builder
from .generator import build_model_parser, generate_field_parser
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
    "ParseField",
    "ParseConfig",
    "build_model_parser",
    "generate_field_parser",
    "parser_builder",
    "literal",
    "pattern",
    "integer",
    "float_num",
    "word",
    "whitespace",
    "any_char",
]