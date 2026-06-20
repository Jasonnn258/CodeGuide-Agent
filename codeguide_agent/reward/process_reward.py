from __future__ import annotations

"""Non-canonical exploratory process score.

The canonical reward used by real evaluation entry points is
`codeguide_agent.reward.calculator.calculate_reward`. This module is retained
only for isolated experiments and must not be wired into headline evaluation
commands.
"""

from typing import Any


def calculate_process_reward(metrics: dict[str, Any]) -> dict[str, Any]:
    score = 0.0
    score += 0.2 if metrics.get("gold_file_hit") else 0.0
    score += 0.2 if metrics.get("gold_function_hit") else 0.0
    score += 0.2 if metrics.get("patch_size", 10_000) <= 40 else -0.1
    score += 0.2 if metrics.get("no_test_deletion") else -0.3
    score += 0.2 if metrics.get("no_hardcode") else -0.3
    return {"process_reward_total": round(score, 4)}
