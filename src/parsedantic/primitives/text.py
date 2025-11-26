# src/parsedantic/primitives/text.py
from __future__ import annotations

import parsy

from ..core.parser import Parser


def literal(text: str) -> Parser[str]:
    """Parse exact literal string."""
    return Parser(
        parsy.string(text),
        formatter=lambda _: text,
    )


def pattern(regex: str, flags: int = 0) -> Parser[str]:
    """Parse regex pattern."""
    return Parser(parsy.regex(regex, flags))


def word() -> Parser[str]:
    """Parse alphanumeric word ([A-Za-z0-9_]+)."""
    return Parser(parsy.regex(r"[A-Za-z0-9_]+"))


def string_of(regex_pattern: str = r"\S+") -> Parser[str]:
    """Parse string matching pattern (default: non-whitespace)."""
    return Parser(parsy.regex(regex_pattern))


def whitespace() -> Parser[str]:
    """Parse one or more whitespace characters."""
    return Parser(parsy.regex(r"\s+"))
