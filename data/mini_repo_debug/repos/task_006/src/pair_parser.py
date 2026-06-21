from __future__ import annotations


def parse_pairs(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, value = line.split("=")
        result[key.strip()] = value.strip()
    return result
