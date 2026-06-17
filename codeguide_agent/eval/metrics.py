from __future__ import annotations

from typing import Any


def _rate(items: list[dict[str, Any]], key: str) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if item.get(key)) / len(items)


def _average(items: list[dict[str, Any]], key: str) -> float:
    if not items:
        return 0.0
    return sum(float(item.get(key, 0)) for item in items) / len(items)


def summarize_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "num_tasks": len(results),
        "public_pass_rate": round(_rate(results, "public_pass"), 4),
        "hidden_pass_rate": round(_rate(results, "hidden_pass"), 4),
        "average_changed_files": round(_average(results, "changed_files_count"), 4),
        "average_changed_lines": round(_average(results, "changed_lines_count"), 4),
        "test_file_modified_rate": round(_rate(results, "test_file_modified"), 4),
        "hardcode_flag_rate": round(_rate(results, "hardcode_suspicion"), 4),
        "average_tool_calls": round(_average(results, "tool_calls"), 4),
    }
