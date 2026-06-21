from __future__ import annotations

from pathlib import PurePosixPath


def safe_asset_path(path: str) -> str:
    return str(PurePosixPath(path))
