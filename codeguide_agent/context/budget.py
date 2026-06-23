from __future__ import annotations

from codeguide_agent.context.schemas import ContextBudget, ContextItem, ContextPack, ItemRole

_PRIORITY: dict[ItemRole, int] = {
    ItemRole.ISSUE: 10,
    ItemRole.SYSTEM: 9,
    ItemRole.TEST_SUMMARY: 8,
    ItemRole.REPO_MAP: 7,
    ItemRole.RETRIEVED_FILE: 5,
    ItemRole.TOOL_TRACE: 3,
    ItemRole.HISTORY_RAG: 4,
}


def apply_budget(pack: ContextPack, budget: ContextBudget | None = None) -> ContextPack:
    if budget is None:
        budget = pack.budget
    used = 0
    available = budget.available
    # sort by priority descending, then by token_estimate ascending (keep smaller items)
    sorted_items = sorted(pack.items, key=lambda item: (-_PRIORITY.get(item.role, 0), item.token_estimate))
    for item in sorted_items:
        if used + item.token_estimate <= available:
            used += item.token_estimate
        else:
            item.dropped = True
            item.drop_reason = f"budget_exceeded: used={used}, needed={item.token_estimate}, available={available}"
    pack.budget = budget
    return pack


def estimate_tokens(text: str) -> int:
    """Simple token estimator: ~4 chars per token."""
    return max(1, len(text) // 4)
