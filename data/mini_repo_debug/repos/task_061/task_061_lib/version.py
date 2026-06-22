from __future__ import annotations


def parse_version(version_str: str) -> tuple[int, ...]:
    parts = version_str.split(".")
    return tuple(int(p) for p in parts)
