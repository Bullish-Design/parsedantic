# tests/test_forward_refs.py
from __future__ import annotations

"""Forward reference resolution tests (Step 14).

These tests exercise recursive ``ParsableModel`` definitions that rely on
string annotations and lazy parser resolution.
"""

import pytest

from parsedantic import ParsableModel, literal


def test_self_referential_linked_list_with_string_annotation() -> None:
    """Singly linked list using a string forward reference for the tail field."""

    class Node(ParsableModel):
        value: int
        next: "Node | None"

        class ParseConfig:
            field_separator = literal("->")
            strict_optional = False

    # Single node with no explicit tail.
    single = Node.parse("1")
    assert isinstance(single, Node)
    assert single.value == 1
    assert single.next is None

    # Multi-node chain where each ``next`` is another ``Node`` instance.
    chain = Node.parse("1->2->3")
    assert isinstance(chain, Node)
    assert chain.value == 1
    assert isinstance(chain.next, Node)
    assert chain.next.value == 2
    assert isinstance(chain.next.next, Node)
    assert chain.next.next.value == 3
    assert chain.next.next.next is None


def test_nested_model_uses_forward_referenced_type() -> None:
    """Nested models should be able to refer to yet-to-be-built models by name."""

    class Node(ParsableModel):
        value: int
        next: "Node | None"

        class ParseConfig:
            field_separator = literal("->")
            strict_optional = False

    class Wrapper(ParsableModel):
        head: Node

    result = Wrapper.parse("1->2")
    assert isinstance(result.head, Node)
    assert result.head.value == 1
    assert result.head.next is not None
    assert result.head.next.value == 2
    assert result.head.next.next is None


def test_unresolved_forward_reference_raises_clear_error() -> None:
    """Forward references to unknown types should fail with a helpful error."""

    class Bad(ParsableModel):
        value: "DoesNotExist"

    with pytest.raises(TypeError) as excinfo:
        Bad.parse("x")

    message = str(excinfo.value)
    assert "Unresolved forward reference" in message
    assert "Bad" in message
