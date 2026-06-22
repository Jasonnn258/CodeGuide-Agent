from __future__ import annotations


def resolve_path(base: str, relative: str) -> str:
    if relative.startswith("/"):
        return relative
    return base.rstrip("/") + "/" + relative
