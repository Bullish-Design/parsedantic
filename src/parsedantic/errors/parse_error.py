# src/parsedantic/errors/parse_error.py
from __future__ import annotations

from typing import Any


class ParseError(Exception):
    """Error with position tracking."""

    def __init__(self, text: str, index: int, expected: str, field_name: str | None = None):
        self.text = text
        self.index = index
        self.expected = expected
        self.field_name = field_name
        self.line, self.column = self._get_line_column(text, index)

        field_part = f" (field '{field_name}')" if field_name else ""
        message = f"Parse error at line {self.line}, column {self.column}{field_part}: expected {expected}"
        super().__init__(message)

    @staticmethod
    def _get_line_column(text: str, index: int) -> tuple[int, int]:
        """Convert character index to (line, column)."""
        if index < 0:
            index = 0
        if index > len(text):
            index = len(text)

        line = text.count("\n", 0, index) + 1
        last_newline = text.rfind("\n", 0, index)

        if last_newline == -1:
            column = index + 1
        else:
            column = index - last_newline

        if column <= 0:
            column = 1

        return line, column

    def error_dict(self) -> dict[str, Any]:
        """Pydantic-compatible error dict."""
        return {
            "type": "parse_error",
            "loc": (self.field_name,) if self.field_name else (),
            "msg": str(self),
            "input": self.text,
            "ctx": {
                "line": self.line,
                "column": self.column,
                "expected": self.expected,
            },
        }

    def __str__(self) -> str:
        """Format with context line and caret."""
        field_part = f" (field '{self.field_name}')" if self.field_name else ""
        lines = [
            f"Parse error at line {self.line}, column {self.column}{field_part}: expected {self.expected}"
        ]

        if self.text:
            text_lines = self.text.splitlines()
            if 0 <= self.line - 1 < len(text_lines):
                context = text_lines[self.line - 1]
                lines.append(context)
                caret_line = " " * (self.column - 1) + "^"
                lines.append(caret_line)

        return "\n".join(lines)


def convert_parsy_error(parsy_error: Exception, text: str, field_name: str | None = None) -> ParseError:
    """Convert parsy ParseError to our ParseError."""
    index = getattr(parsy_error, "index", 0)
    expected_raw = getattr(parsy_error, "expected", str(parsy_error))

    if isinstance(expected_raw, (set, frozenset)):
        expected = ", ".join(sorted(str(e) for e in expected_raw))
    else:
        expected = str(expected_raw)

    return ParseError(text=text, index=index, expected=expected, field_name=field_name)
