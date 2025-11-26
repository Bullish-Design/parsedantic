# src/parsedantic/model/base.py
from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from ..errors import ParseError, convert_parsy_error
from .parser_builder import build_model_parser


class ParsableModel(BaseModel):
    """BaseModel with text parsing."""

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Parse text into validated model."""
        parser = build_model_parser(cls)

        try:
            data = parser.parse(text)
        except ParseError:
            # Already a converted parse error, just propagate
            raise
        except Exception as exc:  # pragma: no cover - defensive
            # Convert any parsing-related error to our ParseError
            raise convert_parsy_error(exc, text) from exc

        return cls.model_validate(data)

    @classmethod
    def from_text_partial(cls, text: str) -> tuple[Self, str]:
        """Parse prefix, return (model, remainder)."""
        parser = build_model_parser(cls)

        try:
            data, remainder = parser.parse_partial(text)
        except ParseError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise convert_parsy_error(exc, text) from exc

        return cls.model_validate(data), remainder
