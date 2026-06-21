from __future__ import annotations

from pathlib import Path


def asset_path(base_dir: str, name: str) -> Path:
    return Path(base_dir) / name
