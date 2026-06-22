from __future__ import annotations


def strip_accents(text: str) -> str:
    replacements = {"\u00e9": "e", "\u00fc": "u", "\u00e0": "a"}
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text
