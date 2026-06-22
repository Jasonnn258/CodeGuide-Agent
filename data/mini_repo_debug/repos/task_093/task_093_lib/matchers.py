from __future__ import annotations


def filter_by_prefix(items: list[str], prefix: str) -> list[str]:
    return [item for item in items if item.startswith(prefix)]
