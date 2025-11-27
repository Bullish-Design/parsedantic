# src/parsedantic/codec.py
"""Text codec system for Parsedantic.

The TextCodec class centralizes parsing and serialization logic:

Architecture:
    ParsableModel.from_text() → TextCodec.parse() → Parser
    ParsableModel.to_text() → TextCodec.serialize() → formatted text

Benefits:
    - Automatic caching (one codec per model class)
    - Single source of truth for configuration
    - Easier testing and debugging
    - Better performance (no repeated parser building)

Example:
    class Point(ParsableModel):
        x: int
        y: int

    # Codec built once, cached automatically
    p1 = Point.from_text("10 20")  # builds codec
    p2 = Point.from_text("15 25")  # reuses codec

    # Introspection available
    codec = Point._get_codec()
    print(codec.separator_str)  # " "
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_type_hints

import parsy

from .core.parser import Parser
from .config import get_field_separator
from .inference import get_parser_for_field
from .model.separator import get_separator_string

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .model import ParsableModel


class TextCodec:
    """Handles parsing and serialization for a ParsableModel class.

    Why this class exists:
    - Centralizes all parsing/serialization logic
    - Caches parsers (built once, reused many times)
    - Single source of truth for configuration
    - Makes testing easier

    The codec is model-class-specific, not instance-specific.
    One codec per model class, shared across all instances.
    """

    def __init__(self, model_class: type[ParsableModel]):
        """Initialize codec for a model class.

        Args:
            model_class: The ParsableModel subclass this codec handles
        """
        self.model_class = model_class

        # Extract configuration once
        self.separator_str = get_separator_string(model_class)
        # Parser version of separator (used for parsing)
        self.separator_parser = get_field_separator(model_class)

        # Build parsers once (expensive operation)
        self.field_parsers = self._build_field_parsers()
        self.combined_parser = self._build_combined_parser()


    def _build_field_parsers(self) -> list[tuple[str, Parser]]:
        """Build parser for each field.

        Strategy:
        - Prefer Pydantic's resolved ``field_info.annotation``.
        - Fall back to evaluated type hints only when needed.

        Using ``field_info.annotation`` avoids issues with
        ``from __future__ import annotations`` where ``__annotations__``
        may contain strings instead of real types.
        """
        try:
            # Use include_extras to preserve Annotated/Parsed metadata
            hints = get_type_hints(self.model_class, include_extras=True)  # type: ignore[call-arg]
        except Exception:
            hints = {}

        fields = self.model_class.model_fields
        field_parsers: list[tuple[str, Parser]] = []

        for field_name, field_info in fields.items():
            # Start with Pydantic's resolved annotation
            annotation = getattr(field_info, "annotation", None)

            # If annotation is missing or very generic, try type hints
            if annotation is None or annotation is Any:
                annotation = hints.get(field_name, annotation)

            parser = get_parser_for_field(annotation)

            if parser is None:
                raise TypeError(
                    f"Cannot generate parser for field '{field_name}' "
                    f"with type {annotation}"
                )

            if getattr(field_info, "description", None):
                parser = parser.desc(field_info.description)

            field_parsers.append((field_name, parser))

        return field_parsers
    def _build_combined_parser(self) -> Parser:
        """Combine field parsers into single dict-producing parser.

        This replaces the old ``build_model_parser`` helper and keeps the
        logic close to where configuration and field parsers live.
        """
        # No fields: parser that always returns empty dict
        if not self.field_parsers:
            return Parser(parsy.success({}))

        separator = self.separator_parser
        field_parsers = self.field_parsers

        # Build sequence: field1, sep, field2, sep, field3, ...
        parsers = [field_parsers[0][1]._parser]
        for _, field_parser in field_parsers[1:]:
            parsers.append(separator._parser)
            parsers.append(field_parser._parser)

        # Combine with parsy.seq
        parsy_parser = parsy.seq(*parsers)

        # Convert tuple result to dict of field_name -> value
        def to_dict(values: tuple) -> dict[str, Any]:
            # Extract field values (skip separators at odd indices)
            field_values = [values[i] for i in range(0, len(values), 2)]
            field_names = [name for name, _ in field_parsers]
            return dict(zip(field_names, field_values))

        return Parser(parsy_parser.map(to_dict))


    def parse(self, text: str) -> "ParsableModel":
        """Parse text into validated model instance.

        Why in codec: Parsing uses the cached combined_parser.
        """
        from .errors import convert_parsy_error

        try:
            data = self.combined_parser.parse(text)
        except Exception as e:  # pragma: no cover - error path
            raise convert_parsy_error(e, text) from e

        return self.model_class.model_validate(data)

    def parse_partial(self, text: str) -> tuple["ParsableModel", str]:
        """Parse text prefix, return (model, remainder).

        Why in codec: Same as parse, but uses parse_partial.
        """
        from .errors import convert_parsy_error

        try:
            data, remainder = self.combined_parser.parse_partial(text)
        except Exception as e:  # pragma: no cover - error path
            raise convert_parsy_error(e, text) from e

        return self.model_class.model_validate(data), remainder

    def serialize(self, instance: "ParsableModel") -> str:
        """Serialize model instance to text.

        Why in codec: Serialization uses cached field_parsers and separator_str.
        Much faster than rebuilding every time.
        """
        parts = [
            parser.format(getattr(instance, field_name))
            for field_name, parser in self.field_parsers
        ]
        return self.separator_str.join(parts)