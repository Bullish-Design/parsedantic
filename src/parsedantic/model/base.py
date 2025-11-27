# src/parsedantic/model/base.py
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Self

from pydantic import BaseModel

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ..codec import TextCodec


class ParsableModel(BaseModel):
    """BaseModel with text parsing via TextCodec.

    The heavy lifting is done by :class:`TextCodec` which:
    - Builds and caches parsers once per model class.
    - Handles configuration such as separators.
    - Centralizes parse/serialize error handling.
    """

    # One codec per model class, shared by all instances
    _text_codec: ClassVar["TextCodec | None"] = None  # type: ignore[valid-type]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _get_codec(cls) -> "TextCodec":
        """Get or create the TextCodec for this model class.

        The codec is cached on the class to avoid rebuilding parsers
        on every parse/serialize call.
        """
        if cls._text_codec is None:
            # Local import to avoid circular dependency at import time
            from ..codec import TextCodec

            cls._text_codec = TextCodec(cls)
        return cls._text_codec

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def from_text(cls, text: str) -> Self:
        """Parse text into a validated model instance.

        This method is the primary user-facing entry point and simply
        delegates to the class codec.
        """
        return cls._get_codec().parse(text)

    @classmethod
    def from_text_partial(cls, text: str) -> tuple[Self, str]:
        """Parse a prefix of ``text``, returning ``(model, remainder)``."""
        return cls._get_codec().parse_partial(text)

    def to_text(self) -> str:
        """Serialize this model instance to text."""
        return type(self)._get_codec().serialize(self)
