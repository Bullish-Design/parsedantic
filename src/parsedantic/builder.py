# src/parsedantic/builder.py
from __future__ import annotations

"""Generator-style parser construction helpers.

This module defines the :func:`parser_builder` decorator which turns a generator
method into a factory for parsy :class:`~parsy.Parser` instances. It is an
escape hatch for complex parsing logic that does not fit the declarative,
field-driven model.

Typical usage overrides :meth:`ParsableModel._build_parser`::

    class Hollerith(ParsableModel):
        content: str

        @parser_builder
        @classmethod
        def _build_parser(cls):
            length = yield pattern(r"\d+").map(int)
            yield literal("H")
            chars = yield any_char.times(length)
            return {"content": "".join(chars)}

The decorated method must be a *generator function* that yields parsy parsers
and finally returns a mapping suitable for
:meth:`pydantic.BaseModel.model_validate`.

"""

from functools import wraps
from inspect import isgeneratorfunction
from types import FunctionType, MethodType
from typing import Any, Callable, TypeVar, cast

from parsy import Parser, generate

F = TypeVar("F", bound=Callable[..., Any])


def _wrap_generator_function(func: Callable[..., Any]) -> Callable[..., Parser[Any]]:
    """Wrap a generator function in a factory that produces a parsy Parser.

    The returned callable has the same signature as *func* but returns a
    :class:`Parser` instead of a generator. Each call creates a fresh parser.
    """
    if not isgeneratorfunction(func):
        raise TypeError(
            "@parser_builder can only be applied to generator functions; "
            f"got {func!r}"
        )

    @wraps(func)
    def factory(*args: Any, **kwargs: Any) -> Parser[Any]:
        @generate
        def parser() -> Any:
            # Delegate the generator protocol to the user function.
            result = yield from func(*args, **kwargs)
            return result

        return parser

    return factory


def parser_builder(method: F) -> F:
    """Decorator for generator-based parser construction.

    When applied to a generator method, this decorator returns a new callable
    that, when invoked, produces a parsy :class:`Parser`. The common pattern is
    to use it on a ``@classmethod`` overriding :meth:`ParsableModel._build_parser`::

        class Model(ParsableModel):
            field: int

            @parser_builder
            @classmethod
            def _build_parser(cls):
                value = yield integer()
                return {"field": value}

    The decorator supports both plain functions and ``@classmethod`` objects.
    In the latter case the classmethod binding is preserved.
    """
    # Handle the common ``@parser_builder @classmethod`` pattern.
    if isinstance(method, classmethod):
        func = method.__func__
        wrapped = _wrap_generator_function(func)

        @classmethod  # type: ignore[misc]
        @wraps(func)
        def wrapper(cls: Any, *args: Any, **kwargs: Any) -> Parser[Any]:
            return wrapped(cls, *args, **kwargs)

        return cast(F, wrapper)

    # Plain function / method case
    if not isinstance(method, (FunctionType, MethodType)):
        raise TypeError("@parser_builder must decorate a function or classmethod")

    wrapped = _wrap_generator_function(method)
    return cast(F, wrapped)
