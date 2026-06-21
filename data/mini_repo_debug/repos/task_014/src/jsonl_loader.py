from __future__ import annotations

import json


def load_json_lines(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        rows.append(json.loads(line))
    return rows
