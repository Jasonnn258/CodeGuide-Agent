from __future__ import annotations


def enrich(record: dict, lookup: dict[str, str]) -> dict:
    result = dict(record)
    result["full_name"] = lookup.get(record.get("id", ""), "Unknown")
    return result
