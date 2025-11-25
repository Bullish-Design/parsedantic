# tests/test_types.py
from __future__ import annotations

from typing import Any

from parsy import regex
from parsedantic.types import Parsable


class ConcreteParsable:
    """Simple concrete implementation used for protocol checks."""

    @classmethod
    def parse(cls, text: str) -> Any:  # pragma: no cover - trivial implementation
        return text

    @classmethod
    def _get_parser(cls):  # pragma: no cover - trivial implementation
        return regex(r".*")


class NotParsable:
    """Missing required protocol methods."""

    def something_else(self) -> None:  # pragma: no cover - helper
        ...


def test_parsable_protocol_accepts_structurally_compatible_types() -> None:
    # runtime_checkable allows isinstance checks based on structural typing
    assert isinstance(ConcreteParsable, Parsable)  # type: ignore[arg-type]
    # Instances should also satisfy the protocol.
    assert isinstance(ConcreteParsable(), Parsable)


def test_parsable_protocol_rejects_incompatible_types() -> None:
    assert not isinstance(NotParsable(), Parsable)
