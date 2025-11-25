# src/parsedantic/config.py
from __future__ import annotations

"""Parsing configuration helpers.

This module defines :class:`ParseConfig` and :func:`get_parse_config`, which are
used by the parser generator to control model-level parsing behaviour.

Each :class:`ParsableModel` subclass may define its own inner ``ParseConfig``
class to override the defaults. Configuration is *not* inherited between model
classes: if a model does not define an inner ``ParseConfig`` it uses the global
defaults defined here.
"""

from typing import TYPE_CHECKING, Type

from parsy import Parser

if TYPE_CHECKING:  # pragma: no cover
    from .models import ParsableModel


class ParseConfig:
    """Configuration container for model parsing behaviour.

    Users typically subclass this as an inner ``ParseConfig`` on a
    :class:`ParsableModel` subclass, overriding one or more attributes.
    """

    #: Parser consumed between successive fields, if any.
    field_separator: Parser | None = None
    #: Controls optional-field behaviour; used by Optional[T] handling.
    strict_optional: bool = True
    #: Optional whitespace parser that may be used between fields.
    whitespace: Parser | None = None


def get_parse_config(model_class: type["ParsableModel"]) -> type[ParseConfig]:
    """Return the :class:`ParseConfig` class for *model_class*.

    The lookup deliberately avoids inheriting configuration from base classes:
    it inspects ``model_class.__dict__`` directly. If a model does not define
    an inner ``ParseConfig`` class the default :class:`ParseConfig` defined in
    this module is returned instead.
    """
    config_cls: Type[ParseConfig] | None = model_class.__dict__.get(
        "ParseConfig"  # type: ignore[assignment]
    )
    if config_cls is None:
        return ParseConfig
    return config_cls
