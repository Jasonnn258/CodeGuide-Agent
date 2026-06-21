from __future__ import annotations

import json


def is_enabled(raw_json: str) -> bool:
    config = json.loads(raw_json)
    return bool(config.get("enabled", False))
