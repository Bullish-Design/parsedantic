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

import logging
from threading import RLock

from parsy import Parser, ParseError as ParsyParseError, forward_declaration
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from .errors import ParseError
from .generator import build_model_parser

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
    _parser_cache_lock: ClassVar[RLock] = RLock()

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
        """Return a cached parser for *cls*, building it on first use.

        The parser is cached per concrete subclass to avoid the overhead of
        regenerating parsers on every :meth:`parse` call. This method is
        thread-safe and emits debug logs indicating whether a cached parser
        was used or a new one was built.

        For recursive models we use :func:`parsy.forward_declaration` so that
        nested references to the same model (or mutually recursive models)
        can obtain a placeholder parser while the real parser is being built.
        """
        placeholder: Parser[Any] | None = None
        with cls._parser_cache_lock:
            parser = cls._parser_cache.get(cls)
            if parser is None:
                logger.debug("Building new parser for %s", cls.__name__)
                placeholder = forward_declaration()
                cls._parser_cache[cls] = placeholder
            else:
                logger.debug("Using cached parser for %s", cls.__name__)
                return parser

        # Build the real parser outside the lock
        built = cls._build_parser()

        with cls._parser_cache_lock:
            current = cls._parser_cache.get(cls)
            # If the cache still contains our placeholder, finalise it.
            if placeholder is not None and current is placeholder:
                placeholder.become(built)
                cls._parser_cache[cls] = built
                return built

            # Another thread may have populated the cache while we built.
            # In that case, prefer the cached instance.
            if current is not None:
                return current

            # Fallback: store and return the built parser.
            cls._parser_cache[cls] = built
            return built

    @classmethod
    def _clear_parser_cache(cls) -> None:
        """Clear the cached parser for this class.

        Primarily intended for tests and benchmarks where parser construction
        needs to be forced on subsequent calls.
        """
        with cls._parser_cache_lock:
            cls._parser_cache.pop(cls, None)

    @classmethod
    def _build_parser(cls: Type[SelfParsableModel]) -> Parser[Any]:
        """Build a parsy ``Parser`` for *cls*.

        The default implementation delegates to :func:`build_model_parser`,
        which uses type annotations (and later, ``ParseField`` metadata) to
        construct a parser for the model.
        """
        return build_model_parser(cls)
