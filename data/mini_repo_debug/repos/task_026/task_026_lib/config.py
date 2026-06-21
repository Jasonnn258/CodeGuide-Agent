from __future__ import annotations

import json


def load_config(text: str) -> dict:
    """Load a JSON config string."""
    return json.loads(text)
