# src/parsedantic/parsers.py
from __future__ import annotations

"""Primitive parser builder functions built on top of parsy.

These functions provide a small, well-typed surface over the underlying parsy
APIs so that higher level code does not need to import parsy directly.
"""

from typing import Any

from parsy import Parser, any_char as _any_char, regex, string


def literal(text: str) -> Parser[str]:
    """Return a parser that matches ``text`` exactly.

    Examples:
        >>> literal("hello").parse("hello")
        'hello'
    """
    return string(text)


def pattern(regex_pattern: str) -> Parser[str]:
    r"""Return a parser that matches the given regular expression.

    Examples:
        >>> pattern(r"\d+").parse("123")
        '123'
    """
    return regex(regex_pattern)


def integer() -> Parser[int]:
    r"""Return a parser that parses a signed base-10 integer.

    The accepted pattern is ``-?\d+`` and the result is mapped to ``int``.
    """
    return regex(r"-?\d+(?![.eE])").map(int)


def float_num() -> Parser[float]:
    r"""Return a parser that parses a floating point number.

    Supported formats include:

    * plain integers: ``"10"`` -> ``10.0``
    * decimals: ``"3.14"``, ``".5"``, ``"10."``
    * scientific notation: ``"1e3"``, ``"-2.5E-4"``
    """
    float_pattern = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
    return regex(float_pattern).map(float)


def word() -> Parser[str]:
    """Return a parser that parses an alphanumeric ``word``.

    The underlying pattern is ``[A-Za-z0-9_]+``.
    """
    return regex(r"[A-Za-z0-9_]+")


def whitespace() -> Parser[str]:
    """Return a parser that parses one or more whitespace characters."""
    return regex(r"\s+")


# Expose ``any_char`` as a ready-to-use parser instead of a factory so that it
# can be used directly with combinators like ``times``.
any_char: Parser[str] = _any_char
