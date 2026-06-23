from __future__ import annotations

from codeguide_agent.context.schemas import ContextItem, ContextPack, ItemRole


def build_context_summary(pack: ContextPack) -> str:
    """Render a compact debug summary of the context pack."""
    lines = ["[ContextPack summary]"]
    lines.append(f"  total items: {len(pack.items)}")
    lines.append(f"  active: {len(pack.active_items)}, dropped: {len(pack.dropped_items)}")
    lines.append(f"  token budget: {pack.budget.max_tokens}, used: {pack.total_tokens}")
    for item in pack.dropped_items:
        lines.append(f"  [DROPPED] {item.role.value}: {item.drop_reason}")
    return "\n".join(lines)


def validate_no_leakage(pack: ContextPack) -> list[str]:
    """Check for forbidden content in the context pack."""
    violations: list[str] = []
    forbidden_patterns = [
        "gold.patch",
        "hidden_test",
        "tests_hidden",
        "gold_patch",
        "oracle",
        "evaluator_only",
    ]
    for item in pack.active_items:
        content_lower = item.content.lower()
        for pat in forbidden_patterns:
            if pat.replace("_", "") in content_lower.replace("_", ""):
                violations.append(f"{item.role.value}: possible leak of '{pat}'")
    return violations
