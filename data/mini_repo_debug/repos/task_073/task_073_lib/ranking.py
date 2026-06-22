from __future__ import annotations


def top_by_score(items: list[dict], key: str, n: int) -> list[dict]:
    return sorted(items, key=lambda d: d[key], reverse=True)[:n]
