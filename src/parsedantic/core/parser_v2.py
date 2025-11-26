# src/parsedantic/core/parser.py
from __future__ import annotations

from typing import Callable, Generic, TypeVar, Any

import parsy

T = TypeVar("T")
U = TypeVar("U")


class Parser(Generic[T]):
    """Bidirectional wrapper around a :mod:`parsy` parser.

    The wrapper provides a small, typed surface:

    * :meth:`parse` delegates to the underlying ``parsy.Parser``.
    * :meth:`format` converts a value back to text using a configurable formatter
      (``str`` by default).
    * ``>>`` composes two parsers, mirroring ``parsy``'s ``>>`` operator while
      keeping bidirectional semantics.

    Primitives and higher-level combinators build on top of this class.
    """

    def __init__(
        self,
        parser: parsy.Parser,
        formatter: Callable[[T], str] | None = None,
    ) -> None:
        self._parser: parsy.Parser = parser
        self._formatter: Callable[[T], str] | None = formatter

    @property
    def inner(self) -> parsy.Parser:
        """Return the underlying :class:`parsy.Parser` instance.

        This is mainly useful for advanced composition where direct access to the
        underlying combinators is needed.
        """

        return self._parser

    def parse(self, text: str) -> T:
        """Parse *text* into a value.

        This is a thin wrapper around :meth:`parsy.Parser.parse` with type
        information attached.
        """

        return self._parser.parse(text)

    def parse_partial(self, text: str) -> tuple[T, str]:
        """Parse *text* and return ``(value, remaining_text)``.

        This mirrors :meth:`parsy.Parser.parse_partial` with type information attached.
        """

        return self._parser.parse_partial(text)

    def format(self, value: T) -> str:
        """Format *value* back into text.

        If no explicit formatter was provided, :func:`str` is used.
        """

        if self._formatter is not None:
            return self._formatter(value)
        return str(value)

    def map(
        self,
        func: Callable[[T], U],
        formatter: Callable[[U], str] | None = None,
    ) -> Parser[U]:
        """Map the parsed value through *func* and return a new parser.

        The new parser reuses the underlying parsy mapping and can optionally
        override the formatter used for :meth:`format`.
        """

        mapped = self._parser.map(func)
        return Parser(mapped, formatter)

    # Sequencing methods

    def then(self, other: Parser[U]) -> Parser[U]:
        """Parse this, then other, return other's result."""
        return Parser(self._parser.then(other._parser), formatter=other._formatter)

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

    def __rshift__(self, other: Parser[U]) -> Parser[U]:
        """Sequence two parsers, discarding the result of the left-hand side.

        This mirrors the behaviour of ``parsy``'s ``>>`` operator. The resulting
        parser uses *other*'s formatter for :meth:`format`.
        """

        combined = self._parser >> other._parser
        return Parser(combined, other._formatter)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Parser({self._parser!r})"

