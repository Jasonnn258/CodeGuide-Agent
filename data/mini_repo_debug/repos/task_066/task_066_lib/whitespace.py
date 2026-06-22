from __future__ import annotations


def collapse_whitespace(text: str) -> str:
    result = text.replace("  ", " ")
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()
