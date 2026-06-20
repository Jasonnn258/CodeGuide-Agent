from __future__ import annotations

"""Non-canonical exploratory outcome score.

The canonical reward used by real evaluation entry points is
`codeguide_agent.reward.calculator.calculate_reward`. This module is retained
only for isolated experiments and must not be wired into headline evaluation
commands.
"""

from typing import Any


def calculate_outcome_reward(metrics: dict[str, Any]) -> dict[str, Any]:
    score = 0.0
    score += 0.4 if metrics.get("public_test_pass") else 0.0
    score += 0.6 if metrics.get("hidden_test_pass") else 0.0
    score -= 0.3 if metrics.get("regression") else 0.0
    return {"outcome_reward_total": round(score, 4)}
