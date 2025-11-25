# tests/test_setup.py
from __future__ import annotations

import importlib
import sys
from types import ModuleType


def test_import_parsedantic() -> None:
    """Basic smoke test: the parsedantic package should be importable."""
    module: ModuleType = importlib.import_module("parsedantic")
    assert module is not None


def test_python_version(python_version: tuple[int, int, int]) -> None:
    """Ensure the running Python version meets the minimum requirement (>=3.9)."""
    major, minor, _ = python_version
    assert (major, minor) >= (3, 9)


def test_dependencies_installed() -> None:
    """Verify core runtime dependencies are importable."""
    pydantic = importlib.import_module("pydantic")
    parsy = importlib.import_module("parsy")
    assert pydantic is not None
    assert parsy is not None
