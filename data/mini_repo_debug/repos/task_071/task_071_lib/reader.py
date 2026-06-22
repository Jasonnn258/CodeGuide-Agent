from __future__ import annotations


def read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""
