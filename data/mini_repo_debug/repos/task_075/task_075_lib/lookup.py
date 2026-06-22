from __future__ import annotations


def case_insensitive_get(mapping: dict[str, str], key: str) -> str | None:
    return mapping.get(key)
