# src/parsedantic/types.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from parsy import Parser


@runtime_checkable
class Parsable(Protocol):
    """Protocol for parsable model-like types.

    Implementations are expected to provide class methods:

    * ``parse(cls, text: str) -> Any`` - parse raw text into an object
    * ``_get_parser(cls) -> Parser`` - return the underlying parsy parser
    """

    @classmethod
    def parse(cls, text: str) -> Any:  # pragma: no cover - structural protocol
        ...

    @classmethod
    def _get_parser(cls) -> Parser:  # pragma: no cover - structural protocol
        ...
