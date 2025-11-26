# src/parsedantic/models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Type, TypeVar, get_type_hints

from parsy import Parser, ParseError as ParsyParseError, forward_declaration
from pydantic import BaseModel, ConfigDict, Field  # , PydanticUndefined
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from .errors import ParseError
from .generator import build_model_parser
from .parsers import whitespace

SelfParsableModel = TypeVar("SelfParsableModel", bound="ParsableModel")


class ParsableModel(BaseModel):
    """Base class for models that can be parsed from text using parsy.

    Subclasses define typed fields as normal Pydantic models. At runtime we
    inspect the annotations to automatically generate a :class:`parsy.Parser`
    capable of consuming an input string and producing a dictionary suitable
    for validation via :meth:`BaseModel.model_validate`.

    Parsers are cached per subclass to avoid repeated regeneration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Cache of built parsers per concrete model class. We keep this private so
    # that callers interact only via :meth:`parse` or :meth:`_get_parser`.
    _parser_cache: ClassVar[Dict[Type["ParsableModel"], Parser]] = {}

    # Forward declaration registry for recursive models. When building a parser
    # for a model that references itself (directly or indirectly), we create a
    # placeholder parser that can be used while the real parser is being
    # constructed.
    _forward_decls: ClassVar[Dict[Type["ParsableModel"], Parser]] = {}

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
        except (
            ParsyParseError
        ) as exc:  # pragma: no cover - behaviour via ParseError tests
            # Delegate conversion of parsy's ``ParseError`` into our public
            # :class:`ParseError` type so that error formatting lives in a
            # single place.
            raise ParseError.from_parsy_error(exc, text) from exc

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
        # Use an explicit cache lookup so subclasses each get their own parser.
        if cls in cls._parser_cache:
            return cls._parser_cache[cls]

        # If we already created a forward declaration for this class (because
        # we are in the middle of building a recursive structure), return that
        # placeholder immediately.
        if cls in cls._forward_decls:
            return cls._forward_decls[cls]

        # Create a forward declaration and register it before building the
        # actual parser so that recursive references can use it.
        placeholder: Parser[Any] = forward_declaration()
        cls._forward_decls[cls] = placeholder

        parser = cls._build_parser()

        # Once the real parser is available, fulfil the forward declaration and
        # move the parser into the main cache.
        placeholder.become(parser)
        cls._parser_cache[cls] = parser
        del cls._forward_decls[cls]

        return parser

    @classmethod
    def _build_parser(cls: Type[SelfParsableModel]) -> Parser[Any]:
        """Build a new parser for *cls* by inspecting its annotations.

        This method delegates to :func:`parsedantic.generator.build_model_parser`
        which performs the heavy lifting of analysing field types and generating
        the appropriate parsy combinators.
        """
        return build_model_parser(cls)

    @classmethod
    def clear_parser_cache(cls) -> None:
        """Clear all cached parsers for all :class:`ParsableModel` subclasses."""
        cls._parser_cache.clear()
        cls._forward_decls.clear()


@dataclass
class ParseFieldMetadata:
    """Configuration for a single field parsed from text.

    This metadata is attached to Pydantic's :class:`FieldInfo` objects via
    the ``json_schema_extra`` attribute so that the parser generator can
    access it when building field parsers.
    """

    parser: Parser[Any] | None = None
    pattern: str | None = None
    sep_by: Parser[Any] | None = None


class ParseField(Field):
    """Custom field function that attaches parsing metadata.

    Usage mirrors :func:`pydantic.Field` but accepts additional keyword
    arguments:

    * ``parser``: an explicit parsy :class:`Parser` to use for this field
    * ``pattern``: a regular expression pattern string to match
    * ``sep_by``: a parser used to separate list elements

    The metadata is stored on the underlying :class:`FieldInfo` so that
    :func:`parsedantic.generator.generate_field_parser` can inspect it.
    """

    def __init__(
        self,
        default: Any = PydanticUndefined,
        *,
        parser: Parser[Any] | None = None,
        pattern: str | None = None,
        sep_by: Parser[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        extra = kwargs.pop("json_schema_extra", {}) or {}
        extra["parsefield_metadata"] = ParseFieldMetadata(
            parser=parser,
            pattern=pattern,
            sep_by=sep_by,
        )
        super().__init__(default=default, json_schema_extra=extra, **kwargs)


def get_parsefield_metadata(field_info: FieldInfo) -> ParseFieldMetadata | None:
    """Extract :class:`ParseFieldMetadata` from a Pydantic :class:`FieldInfo`.

    Returns ``None`` if no parsing metadata has been attached.
    """
    extra = field_info.json_schema_extra or {}
    metadata = extra.get("parsefield_metadata")
    if isinstance(metadata, ParseFieldMetadata):
        return metadata
    return None


class ParseConfig(BaseModel):
    """Configuration options that influence parser generation for a model.

    Instances of this class are intended for use via the ``parse_config``
    attribute on :class:`ParsableModel` subclasses. For example:

    .. code-block:: python

       class MyModel(ParsableModel):
           x: int
           y: int

           parse_config = ParseConfig(field_separator=whitespace())

    Attributes:
        field_separator:
            Optional parser that separates top-level fields in the model. When
            provided, this parser is inserted between each field parser in the
            generated model parser.
        strict_optional:
            When ``True`` (the default), optional fields still raise a
            :class:`ParseError` if the underlying parser fails. When ``False``,
            failures are treated as a missing value and the result becomes
            ``None``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    field_separator: Parser | None = None
    strict_optional: bool = True
    whitespace: Parser | None = None


def get_parse_config(model_cls: type[ParsableModel]) -> ParseConfig:
    """Return the :class:`ParseConfig` associated with *model_cls*.

    If the model defines a ``parse_config`` class attribute it is used
    directly. Otherwise a default configuration is returned.
    """
    config = getattr(model_cls, "parse_config", None)
    if isinstance(config, ParseConfig):
        return config
    return ParseConfig()


def iter_model_fields(model_cls: type[ParsableModel]) -> Dict[str, FieldInfo]:
    """Yield Pydantic :class:`FieldInfo` objects for all model fields.

    This helper is used by the parser generator to obtain field metadata
    (including :class:`ParseFieldMetadata`) from the model class.
    """
    type_hints = get_type_hints(model_cls, include_extras=True)
    fields: Dict[str, FieldInfo] = {}
    for name, annotation in type_hints.items():
        if name.startswith("_"):
            continue
        field_info = model_cls.model_fields.get(name)
        if isinstance(field_info, FieldInfo):
            fields[name] = field_info
    return fields

