# src/parsedantic/errors.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
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
        # Manual init instead of the dataclass-generated one so we can derive line/column.
        self.text = text
        self.index = index
        self.expected = expected
        self.line, self.column = get_line_column(text, index)
        # Do not call super().__init__(str(self)) here; that interacts badly with
        # dataclass(slots=True) + Exception on newer Python versions.
        # String representation is fully handled by __str__.
        Exception.__init__(self)

    def __str__(self) -> str:  # pragma: no cover - behaviour tested via tests
        context_line = _get_context_line(self.text, self.line)
        marker_line = " " * (self.column - 1) + "^"
        return (
            f"ParseError at line {self.line}, column {self.column}: expected {self.expected!r}\n"
            f"{context_line}\n{marker_line}"
        )


def get_line_column(text: str, index: int) -> tuple[int, int]:
    """Translate a character index into one-based (line, column).

    The index is clamped into the valid range ``[0, len(text)]``. Lines and columns are
    both one-based, and line breaks are recognised as ``\"\\n\"`` characters.
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
    # splitlines discards trailing newline characters, which is fine for context.
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return ""
