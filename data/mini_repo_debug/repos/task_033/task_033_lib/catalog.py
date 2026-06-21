from __future__ import annotations


def visible_titles(items: list[dict], category: str) -> list[str]:
    visible = [item for item in items if item.get("visible") and item.get("category") == category]
    return [item["title"] for item in sorted(visible, key=lambda item: item["title"])]
