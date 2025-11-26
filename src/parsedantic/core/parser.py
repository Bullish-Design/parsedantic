# src/parsedantic/core/parser.py
from __future__ import annotations

from typing import Callable, Generic, TypeVar

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

    def __rshift__(self, other: Parser[U]) -> Parser[U]:
        """Sequence two parsers, discarding the result of the left-hand side.

        This mirrors the behaviour of ``parsy``'s ``>>`` operator. The resulting
        parser uses *other*'s formatter for :meth:`format`.
        """

        combined = self._parser >> other._parser
        return Parser(combined, other._formatter)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Parser({self._parser!r})"