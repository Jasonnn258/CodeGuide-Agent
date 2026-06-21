from __future__ import annotations

from pathlib import Path


def safe_join(base_dir: str, user_path: str) -> str:
    return str(Path(base_dir) / user_path)
