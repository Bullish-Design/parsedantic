# src/parsedantic/models.py
from __future__ import annotations

"""Core ``ParsableModel`` base class.

This module defines :class:`ParsableModel`, a thin extension of Pydantic's
``BaseModel`` that adds text parsing capabilities on top of the primitive
parsers and protocols defined in earlier steps.

Step 4 only provides the skeleton and caching infrastructure. Actual parser
generation is introduced in later steps.
"""

from typing import Any, ClassVar, Dict, Type, TypeVar

from parsy import Parser, ParseError as ParsyParseError
from pydantic import BaseModel

from .errors import ParseError

SelfParsableModel = TypeVar("SelfParsableModel", bound="ParsableModel")


class ParsableModel(BaseModel):
    """Base class for models that can parse themselves from text.

    Subclasses gain a :meth:`parse` class method that turns an input string
    into a validated model instance using an underlying parsy ``Parser``. The
    actual parser construction is delegated to :meth:`_build_parser`, whose
    result is cached per subclass in :attr:`_parser_cache`.
    """

    #: Cache mapping model classes to their parser instances.
    _parser_cache: ClassVar[Dict[Type["ParsableModel"], Parser[Any]]] = {}

    class ParseConfig:
        """Default parsing configuration for a model.

        Later steps will make use of these attributes when generating parsers.
        They are defined here so that user code can start declaring configs
        early without breaking imports.
        """

        #: Parser consumed between successive fields, if any.
        field_separator: Parser[Any] | None = None
        #: Behaviour for Optional fields; honoured in later steps.
        strict_optional: bool = True
        #: Optional whitespace handling parser; used in later steps.
        whitespace: Parser[Any] | None = None

    @classmethod
    def parse(cls: Type[SelfParsableModel], text: str) -> SelfParsableModel:
        """Parse *text* into a validated model instance.

        Parsing happens in two phases:

        1. The underlying parsy ``Parser`` is obtained via :meth:`_get_parser`
           and executed on ``text``.
        2. The parsed value is validated using Pydantic's
           :meth:`BaseModel.model_validate`.

        ``ParsyParseError`` exceptions are converted into our own
        :class:`parsedantic.errors.ParseError` type so that callers do not need
        to depend on parsy directly. Validation errors are propagated as-is.
        """
        parser = cls._get_parser()
        try:
            parsed_data = parser.parse(text)
        except ParsyParseError as exc:  # pragma: no cover - behaviour via ParseError tests
            # ``ParseError`` expects the original text, a character index and an
            # expected-description string. parsy's ``ParseError`` exposes
            # ``index`` and ``expected`` attributes; we fall back gracefully if
            # they are absent for any reason.
            index = getattr(exc, "index", 0)
            expected_raw = getattr(exc, "expected", str(exc))
            # parsy's ``expected`` is often a frozenset; normalise to a compact
            # human-readable string for our ``ParseError``.
            if isinstance(expected_raw, (set, frozenset)):
                expected_str = ", ".join(sorted(map(str, expected_raw)))
            else:
                expected_str = str(expected_raw)
            raise ParseError(text=text, index=index, expected=expected_str) from exc

        # Delegate to Pydantic for full validation. Any ``ValidationError``
        # raised here is intentionally not wrapped.
        return cls.model_validate(parsed_data)

    @classmethod
    def _get_parser(cls: Type[SelfParsableModel]) -> Parser[Any]:
        """Return the cached parser for *cls*, building it on first use.

        Subclasses normally do not override this; they instead provide an
        implementation of :meth:`_build_parser`.
        """
        parser = cls._parser_cache.get(cls)
        if parser is None:
            parser = cls._build_parser()
            cls._parser_cache[cls] = parser
        return parser

    @classmethod
    def _build_parser(cls: Type[SelfParsableModel]) -> Parser[Any]:
        """Build a parsy ``Parser`` for *cls*.

        Step 4 only defines the skeleton; concrete parser generation is added
        in Step 5. Subclasses may override this method to provide custom
        parsers directly.
        """
        msg = (
            "Parser generation for ParsableModel subclasses is not implemented yet. "
            "Override ``_build_parser`` on the model class or implement "
            "generator-based construction in later steps."
        )
        raise NotImplementedError(msg)
