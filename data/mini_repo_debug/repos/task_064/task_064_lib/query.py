from __future__ import annotations


def build_query(**params: object) -> str:
    parts = [f"{k}={v}" for k, v in params.items()]
    return "&".join(parts)
