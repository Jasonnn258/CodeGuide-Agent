from __future__ import annotations


def collect_tags(items: list[dict], tags: list[str] = []) -> list[str]:
    for item in items:
        tag = item.get("tag")
        if tag and tag not in tags:
            tags.append(tag)
    return tags
