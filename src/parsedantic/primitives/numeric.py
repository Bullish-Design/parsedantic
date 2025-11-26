# src/parsedantic/primitives/numeric.py
from __future__ import annotations

import parsy

from ..core.parser import Parser


def integer() -> Parser[int]:
    """Parse signed integer."""
    return Parser(
        parsy.regex(r"-?\d+(?![.eE])").map(int),
        formatter=str,
    )


def float_num() -> Parser[float]:
    """Parse float with decimals and scientific notation."""
    float_pattern = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
    return Parser(
        parsy.regex(float_pattern).map(float),
        formatter=str,
    )
