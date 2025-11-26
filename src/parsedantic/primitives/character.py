# src/parsedantic/primitives/character.py
from __future__ import annotations

from typing import Callable

import parsy

from ..core.parser import Parser


any_char: Parser[str] = Parser(parsy.any_char)


def char_from(chars: str) -> Parser[str]:
    """Parse a single character from the given set."""
    return Parser(parsy.char_from(chars))


def string_from(chars: str, min: int = 1, max: int | None = None) -> Parser[str]:
    """Parse a string of characters from the given set.

    When max is provided, the length is constrained between min and max.
    """
    if max is not None:
        return Parser(parsy.string_from(chars, min, max))
    return Parser(parsy.string_from(chars, min))


def test_char(predicate: Callable[[str], bool], description: str = "a character") -> Parser[str]:
    """Parse a single character that satisfies the predicate."""
    return Parser(parsy.test_char(predicate, description))


def test_item(predicate: Callable[[str], bool], description: str = "an item") -> Parser[str]:
    """Parse a single item that satisfies the predicate."""
    return Parser(parsy.test_item(predicate, description))


letter: Parser[str] = Parser(parsy.letter)
digit: Parser[str] = Parser(parsy.digit)
