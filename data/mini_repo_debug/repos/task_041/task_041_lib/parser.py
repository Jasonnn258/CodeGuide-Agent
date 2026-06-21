from __future__ import annotations


def parse_assignment(line: str) -> tuple[str, str]:
    key, value = line.split("=")
    return key.strip(), value.strip()
