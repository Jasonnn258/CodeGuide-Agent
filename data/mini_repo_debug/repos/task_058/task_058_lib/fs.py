from __future__ import annotations

import os


def ensure_dir(path: str) -> None:
    os.makedirs(path)
