# tests/types/test_annotation.py
from __future__ import annotations

from typing import Annotated, get_origin

from parsedantic import Parsed, integer, word
from parsedantic.types import extract_parser, get_value_type


class TestParsedAnnotation:
    def test_creates_annotated_type(self):
        parsed_type = Parsed(int, integer())
        assert get_origin(parsed_type) is Annotated

    def test_preserves_value_type(self):
        parsed_type = Parsed(str, word())
        assert get_value_type(parsed_type) is str

    def test_carries_parser_in_metadata(self):
        parser = integer()
        parsed_type = Parsed(int, parser)
        assert extract_parser(parsed_type) is parser


class TestExtractParser:
    def test_extracts_from_parsed(self):
        parser = word()
        parsed_type = Parsed(str, parser)
        assert extract_parser(parsed_type) is parser

    def test_returns_none_for_plain_type(self):
        assert extract_parser(int) is None
        assert extract_parser(str) is None
