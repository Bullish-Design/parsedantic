# tests/primitives/test_numeric.py
from __future__ import annotations

import pytest
import parsy

from parsedantic.primitives.numeric import float_num, integer


class TestInteger:
    def test_parses_positive(self):
        assert integer().parse("42") == 42

    def test_parses_negative(self):
        assert integer().parse("-17") == -17

    def test_parses_zero(self):
        assert integer().parse("0") == 0

    def test_fails_on_float(self):
        with pytest.raises(parsy.ParseError):
            integer().parse("3.14")

    def test_formats(self):
        assert integer().format(42) == "42"


class TestFloatNum:
    def test_parses_decimal(self):
        assert float_num().parse("3.14") == pytest.approx(3.14)

    def test_parses_scientific(self):
        assert float_num().parse("1e3") == pytest.approx(1000.0)

    def test_parses_negative(self):
        assert float_num().parse("-0.5") == pytest.approx(-0.5)

    def test_formats(self):
        assert float_num().format(3.14) == "3.14"
