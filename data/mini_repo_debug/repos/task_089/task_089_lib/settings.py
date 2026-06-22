from __future__ import annotations

import json


def get_nested(config_json: str, path: str) -> object:
    data = json.loads(config_json)
    for key in path.split("."):
        data = data[key]
    return data
