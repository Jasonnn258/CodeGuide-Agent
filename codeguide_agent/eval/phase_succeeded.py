"""Phase-succeeded computation for bounded rollout/export runner.

Idempotent rule: a phase succeeds when the final state meets all thresholds
and there are no rollout failures — regardless of whether refresh commands
produced non-zero deltas. This avoids false negatives when re-running a phase
whose data is already canonical.

All operations are local. No training, external APIs, or LLM calls.
"""

from __future__ import annotations

from typing import Any

DEFAULT_THRESHOLDS: dict[str, int] = {
    "sft_total": 100,
    "preference_total": 100,
    "preference_bank_total": 100,
    "hard_preference_total": 30,
    "task_total": 100,
}


def compute_phase_succeeded(
    failures: list[dict[str, Any]] | None,
    after_counts: dict[str, int],
    *,
    thresholds: dict[str, int] | None = None,
) -> bool:
    """Return True iff final state meets thresholds and no failures recorded.

    Idempotent: succeeds even when refresh commands produced zero deltas,
    as long as the final state is canonical and no rollout failed.
    """
    if failures:
        return False
    thresholds = thresholds or DEFAULT_THRESHOLDS
    active = after_counts.get("active_task_count", 0)
    planned = after_counts.get("planned_backlog_count", 0)
    task_total = active + planned
    return (
        after_counts.get("sft_total", 0) >= thresholds["sft_total"]
        and after_counts.get("preference_total", 0) >= thresholds["preference_total"]
        and after_counts.get("preference_bank_total", 0) >= thresholds["preference_bank_total"]
        and after_counts.get("hard_preference_total", 0) >= thresholds["hard_preference_total"]
        and task_total >= thresholds["task_total"]
    )
