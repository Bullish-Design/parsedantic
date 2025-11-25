# tests/conftest.py
from __future__ import annotations

import sys
from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def python_version() -> tuple[int, int, int]:
    """Return the current Python version as a (major, minor, micro) tuple."""
    version = sys.version_info
    return version.major, version.minor, version.micro


@pytest.fixture(scope="session")
def env_info(python_version: tuple[int, int, int]) -> dict[str, Any]:
    """Basic environment information useful for debugging tests."""
    major, minor, micro = python_version
    return {
        "python": f"{major}.{minor}.{micro}",
    }
