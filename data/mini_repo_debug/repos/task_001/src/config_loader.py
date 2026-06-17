from __future__ import annotations

import json
from pathlib import Path


def load_config(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)
