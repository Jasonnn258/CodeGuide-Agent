from __future__ import annotations


def page_count(total: int, per_page: int) -> int:
    return total // per_page
