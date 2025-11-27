# src/parsedantic/generator.py
from __future__ import annotations

from functools import wraps
from inspect import isgeneratorfunction
from typing import Any, Callable, TypeVar, cast

import parsy

from .core import Parser

F = TypeVar("F", bound=Callable[..., Any])


def generate(func: F) -> F:
    """Decorator for generator-based parsing.

    The decorated function must be a generator function that yields either
    :class:`Parser` instances or raw :mod:`parsy` parsers. The final return
    value of the generator becomes the result of the composed parser.
    """
    if not isgeneratorfunction(func):
        raise TypeError("@generate requires generator function")

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Parser[Any]:
        @parsy.generate
        def parsy_parser() -> Any:
            gen = func(*args, **kwargs)

            try:
                # Prime the generator to get the first parser.
                parser = gen.send(None)

                while True:
                    # Support both our Parser wrapper and raw parsy parsers.
                    if isinstance(parser, Parser):
                        parsy_p = parser._parser
                    else:
                        parsy_p = parser

                    result = yield parsy_p

                    try:
                        parser = gen.send(result)
                    except StopIteration as e:
                        return e.value
            except StopIteration as e:
                return e.value

        return Parser(parsy_parser)

    return cast(F, wrapper)
