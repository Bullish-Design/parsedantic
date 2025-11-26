# src/parsedantic/primitives/control.py
from __future__ import annotations

from typing import Any, TypeVar

import parsy

from ..core.parser import Parser

T = TypeVar("T")


def success(value: T) -> Parser[T]:
    """Parser that always succeeds with the given value without consuming input."""
    return Parser(parsy.success(value), formatter=lambda _: "")


def fail(expected: str) -> Parser[Any]:
    """Parser that always fails with the given expected message."""
    return Parser(parsy.fail(expected))


def eof() -> Parser[None]:
    """Parser that matches the end of input."""
    return Parser(parsy.eof, formatter=lambda _: "")


def peek(parser: Parser[T]) -> Parser[T]:
    """Lookahead parser that parses without consuming input."""
    return Parser(parsy.peek(parser._parser))


def index() -> Parser[int]:
    """Parser that returns the current input position (character index)."""
    return Parser(parsy.index, formatter=str)


def line_info() -> Parser[tuple[int, int]]:
    """Parser that returns (line, column) of the current position."""
    return Parser(parsy.line_info, formatter=lambda info: f"{info[0]}:{info[1]}")
