# tests/test_forward_refs.py
from __future__ import annotations

from typing import Optional

import pytest

from parsedantic import ParsableModel, ParseError


def test_self_referential_linked_list_with_string_annotation() -> None:
    class Node(ParsableModel):
        value: int
        next: Optional["Node"]

    head = Node.parse("1")
    assert head.value == 1
    assert head.next is None


def test_nested_model_uses_forward_referenced_type() -> None:
    class Tree(ParsableModel):
        value: int
        left: Optional["Tree"]
        right: Optional["Tree"]

    tree = Tree.parse("1")
    assert tree.value == 1
    assert tree.left is None
    assert tree.right is None


def test_unresolved_forward_reference_raises_clear_error() -> None:
    """Forward references to unknown types should fail with a helpful error."""

    class Bad(ParsableModel):
        value: "DoesNotExist"

    with pytest.raises(TypeError) as excinfo:
        Bad.parse("x")

    msg = str(excinfo.value)
    assert "Unresolved forward reference" in msg
    assert "Bad" in msg
