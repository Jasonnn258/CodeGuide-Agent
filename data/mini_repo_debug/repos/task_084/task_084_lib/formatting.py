from __future__ import annotations

from typing import Any


def format_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    columns.sort()
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(str(row.get(c, "")) for c in columns))
    return "\n".join(lines)
