from __future__ import annotations


def split_extension(path: str) -> tuple[str, str]:
    if "." in path:
        base, ext = path.rsplit(".", 1)
        return base, "." + ext
    return path, ""
