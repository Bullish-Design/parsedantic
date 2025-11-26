# tests/primitives/test_text.py
from __future__ import annotations

import pytest
import parsy

from parsedantic.primitives.text import literal, pattern, string_of, whitespace, word


class TestLiteral:
    def test_matches_exact_string(self):
        parser = literal("hello")
        assert parser.parse("hello") == "hello"

    def test_fails_on_mismatch(self):
        parser = literal("hello")
        with pytest.raises(parsy.ParseError):
            parser.parse("world")

    def test_formats_to_original(self):
        parser = literal("test")
        assert parser.format("anything") == "test"


class TestPattern:
    def test_matches_regex(self):
        parser = pattern(r"\d+")
        assert parser.parse("123") == "123"

    def test_fails_on_no_match(self):
        parser = pattern(r"\d+")
        with pytest.raises(parsy.ParseError):
            parser.parse("abc")


class TestWord:
    def test_matches_alphanumeric(self):
        parser = word()
        assert parser.parse("hello123") == "hello123"

    def test_fails_on_whitespace(self):
        parser = word()
        with pytest.raises(parsy.ParseError):
            parser.parse("hello world")


class TestStringOf:
    def test_default_pattern(self):
        parser = string_of()
        assert parser.parse("hello") == "hello"

    def test_custom_pattern(self):
        parser = string_of(r"[a-z]+")
        assert parser.parse("hello") == "hello"
        with pytest.raises(parsy.ParseError):
            parser.parse("Hello")


class TestWhitespace:
    def test_matches_spaces(self):
        parser = whitespace()
        assert parser.parse("   ") == "   "

    def test_matches_mixed_whitespace(self):
        parser = whitespace()
        assert parser.parse(" \t\n") == " \t\n"

    def test_fails_on_empty(self):
        parser = whitespace()
        with pytest.raises(parsy.ParseError):
            parser.parse("")
