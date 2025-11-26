# src/parsedantic/errors.py
from __future__ import annotations

"""Custom error types used by Parsedantic.

This module currently exposes a single :class:`ParseError` exception that
wraps failures coming from the underlying parsy parsers and enriches them with
line/column information and a small source-code style context snippet.

The goal is to provide actionable, implementation-agnostic feedback to callers:
they should never need to depend on parsy's own :class:`ParseError` type.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, init=False)
class ParseError(Exception):
    """Parsing failure with source position information.

    Attributes:
        text: Original input text that was being parsed.
        index: Zero-based character index where the error occurred.
        expected: Human readable description of what was expected.
        line: One-based line number of the error location.
        column: One-based column number of the error location.
    """

    text: str
    index: int
    expected: str
    line: int
    column: int

    def __init__(self, text: str, index: int, expected: str) -> None:
        # Manual init so we can derive line/column eagerly.
        self.text = text
        self.index = index
        self.expected = expected
        self.line, self.column = get_line_column(text, index)
        Exception.__init__(self)

    def __str__(self) -> str:  # pragma: no cover - behaviour tested via tests
        context_line = _get_context_line(self.text, self.line)
        marker_line = " " * (self.column - 1) + "^"
        return (
            f"ParseError at line {self.line}, column {self.column}: "
            f"expected {self.expected!r}\n"
            f"{context_line}\n"
            f"{marker_line}"
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def from_parsy_error(cls, exc: Exception, text: str) -> "ParseError":
        """Construct :class:`ParseError` from a parsy ``ParseError``.

        The *exc* object is treated as duck-typed: if it exposes ``index`` and
        ``expected`` attributes they are used, otherwise sensible fallbacks are
        chosen. ``expected`` values that are sets are normalised into a stable,
        comma-separated string.
        """
        index = getattr(exc, "index", 0)
        expected_raw: Any = getattr(exc, "expected", str(exc))

        if isinstance(expected_raw, (set, frozenset)):
            expected = ", ".join(sorted(map(str, expected_raw)))
        else:
            expected = str(expected_raw)

        return cls(text=text, index=index, expected=expected)


def get_line_column(text: str, index: int) -> tuple[int, int]:
    """Translate a character index into one-based ``(line, column)``.

    The index is clamped into the valid range ``[0, len(text)]``. Lines and
    columns are both one-based, and line breaks are recognised as "\n"
    characters.
    """
    if index < 0:
        index = 0
    if index > len(text):
        index = len(text)

    # Line number is count of preceding newlines + 1.
    line = text.count("\n", 0, index) + 1

    # Column is distance from most recent newline (or start of text) + 1.
    last_newline = text.rfind("\n", 0, index)
    if last_newline == -1:
        column = index + 1
    else:
        column = index - last_newline
    if column <= 0:
        column = 1
    return line, column


def _get_context_line(text: str, line: int) -> str:
    """Return the full line of text for ``line`` (one-based).

    If the line is out of range, an empty string is returned.
    """
    if not text:
        return ""

    lines = text.splitlines()
    # ``splitlines`` discards trailing newline characters, which is fine for context.
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return ""
