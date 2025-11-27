# src/parsedantic/model/serializer.py
from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .base import ParsableModel
    from ..codec import TextCodec  # for type checkers only


def serialize_model(model: "ParsableModel") -> str:
    """Serialize a model instance to text.

    DEPRECATED: This helper is kept for backwards compatibility only.

    New code should call :meth:`ParsableModel.to_text` on the instance or use
    :class:`parsedantic.codec.TextCodec` directly instead. Internally this
    function simply forwards to the model's text codec so that there is a
    single source of truth for serialization behaviour.
    """
    # Local import to avoid an import cycle at module import time
    from ..codec import TextCodec

    warnings.warn(
        "serialize_model is deprecated. Use instance.to_text() or "
        "TextCodec(type(instance)).serialize(instance) instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    model_cls = type(model)

    # Prefer the cached codec used by ParsableModel if available.
    get_codec = getattr(model_cls, "_get_codec", None)
    if callable(get_codec):
        codec = get_codec()  # type: ignore[misc]
    else:
        codec = TextCodec(model_cls)  # type: ignore[arg-type]

    return codec.serialize(model)
