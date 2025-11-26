# src/parsedantic/core/parser.py
from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

import parsy

T = TypeVar("T")
U = TypeVar("U")


class Parser(Generic[T]):
    """Wrapper around parsy.Parser with serialization."""

    def __init__(
        self,
        parser: parsy.Parser,
        formatter: Callable[[T], str] | None = None,
    ):
        self._parser = parser
        self._formatter = formatter or str

    def parse(self, text: str) -> T:
        """Parse text into value."""
        return self._parser.parse(text)

    def parse_partial(self, text: str) -> tuple[T, str]:
        """Parse prefix of text, return (value, remainder)."""
        return self._parser.parse_partial(text)

    def format(self, value: T) -> str:
        """Format value back to text."""
        return self._formatter(value)

    # Transformation methods

    def map(self, fn: Callable[[T], U]) -> Parser[U]:
        """Transform parser result."""
        return Parser(self._parser.map(fn), self._formatter)

    def bind(self, fn: Callable[[T], Parser[U]]) -> Parser[U]:
        """Monadic bind operation."""

        def parsy_bind(x: T) -> parsy.Parser:
            result = fn(x)
            return result._parser

        return Parser(self._parser.bind(parsy_bind))

    # Sequencing methods

    def then(self, other: Parser[U]) -> Parser[U]:
        """Parse this, then other, return other's result."""
        return Parser(self._parser.then(other._parser))

    def skip(self, other: Parser[Any]) -> Parser[T]:
        """Parse this, then other, return this result."""
        return Parser(self._parser.skip(other._parser))

    # Operators

    def __rshift__(self, other: Parser[U]) -> Parser[U]:
        """Operator: self >> other (then)."""
        return self.then(other)

    def __lshift__(self, other: Parser[Any]) -> Parser[T]:
        """Operator: self << other (skip)."""
        return self.skip(other)

    def __or__(self, other: Parser[T]) -> Parser[T]:
        """Operator: self | other (alternative)."""
        return Parser(self._parser | other._parser)

    # Combinator methods

    def desc(self, description: str) -> Parser[T]:
        """Set description for error messages."""
        return Parser(self._parser.desc(description), self._formatter)

    def optional(self) -> Parser[T | None]:
        """Make parser optional."""
        return Parser(self._parser.optional(), self._formatter)

    def many(self) -> Parser[list[T]]:
        """Parse zero or more occurrences."""
        return Parser(
            self._parser.many(),
            lambda values: " ".join(self._formatter(v) for v in values),
        )

    def times(
        self,
        n: int,
        min: int | None = None,
        max: int | None = None,
    ) -> Parser[list[T]]:
        """Parse exactly n times, or between min and max."""
        if min is not None or max is not None:
            parser = self._parser.times(n, min or 0, max)
        else:
            parser = self._parser.times(n)
        return Parser(parser)

    def sep_by(
        self,
        sep: Parser[Any],
        *,
        min: int = 0,
        max: int | None = None,
    ) -> Parser[list[T]]:
        """Parse separated list."""
        if max is not None:
            parser = self._parser.sep_by(sep._parser, min=min, max=max)
        else:
            parser = self._parser.sep_by(sep._parser, min=min)

        sep_str = " "
        return Parser(
            parser,
            lambda values: sep_str.join(self._formatter(v) for v in values),
        )

    def result(self, value: U) -> Parser[U]:
        """Replace result with constant value."""
        return Parser(self._parser.result(value))

    def concat(self) -> Parser[str]:
        """Concatenate list of strings."""
        return Parser(self._parser.concat())

