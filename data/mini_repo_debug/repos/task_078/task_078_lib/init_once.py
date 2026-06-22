from __future__ import annotations

from typing import Any

_INITIALIZED: dict[str, Any] = {}


def initialize(key: str, factory: Any) -> Any:
    if key not in _INITIALIZED:
        _INITIALIZED[key] = factory() if callable(factory) else factory
    return _INITIALIZED[key]
