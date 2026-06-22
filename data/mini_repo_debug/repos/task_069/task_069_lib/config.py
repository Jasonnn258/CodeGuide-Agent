from __future__ import annotations

import json


def get_list(config_json: str, key: str) -> list:
    config = json.loads(config_json)
    return config.get(key)
