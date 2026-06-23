from __future__ import annotations

from codeguide_agent.context.budget import apply_budget, estimate_tokens
from codeguide_agent.context.compaction import compact_run_test
from codeguide_agent.context.manager import ContextManager
from codeguide_agent.context.pack_builder import build_context_summary
from codeguide_agent.context.schemas import ContextBudget, ContextItem, ContextPack, ItemRole


def test_context_item_creation():
    item = ContextItem(role=ItemRole.ISSUE, content="fix parsing bug", token_estimate=10)
    assert item.role == ItemRole.ISSUE
    assert item.content == "fix parsing bug"
    assert item.dropped is False


def test_context_pack_basics():
    pack = ContextPack(items=[
        ContextItem(role=ItemRole.ISSUE, content="issue text", token_estimate=100),
        ContextItem(role=ItemRole.TEST_SUMMARY, content="tests passed", token_estimate=50),
    ])
    assert pack.total_tokens == 150
    assert len(pack.active_items) == 2
    text = pack.to_prompt_text()
    assert "issue text" in text
    assert "tests passed" in text


def test_budget_drops_low_priority_items():
    budget = ContextBudget(max_tokens=1000, reserved_system_tokens=0, reserved_tool_output_tokens=0)
    pack = ContextPack(items=[
        ContextItem(role=ItemRole.ISSUE, content="a" * 400, token_estimate=100),
        ContextItem(role=ItemRole.TOOL_TRACE, content="b" * 4000, token_estimate=1000),
    ], budget=budget)
    pack = apply_budget(pack)
    # ISSUE is high priority, should survive; TOOL_TRACE is low, drops
    assert pack.items[0].dropped is False
    assert pack.items[1].dropped is True
    assert "budget_exceeded" in pack.items[1].drop_reason


def test_budget_fits_all_when_under_limit():
    budget = ContextBudget(max_tokens=10000, reserved_system_tokens=0, reserved_tool_output_tokens=0)
    pack = ContextPack(items=[
        ContextItem(role=ItemRole.ISSUE, content="x", token_estimate=10),
        ContextItem(role=ItemRole.TEST_SUMMARY, content="y", token_estimate=10),
    ], budget=budget)
    pack = apply_budget(pack)
    assert all(not item.dropped for item in pack.items)


def test_compaction_truncates_long_test_output():
    lines = ["line " + str(i) for i in range(100)]
    item = ContextItem(role=ItemRole.TEST_SUMMARY, content="\n".join(lines), token_estimate=500)
    result = compact_run_test(item)
    assert result.meta["compacted"] is True
    assert len(result.content.split("\n")) < 100


def test_compaction_preserves_failure_signal():
    lines = ["line " + str(i) for i in range(50)]
    lines.append("FAILED test_foo - AssertionError")
    lines.extend("line " + str(i) for i in range(50, 100))
    item = ContextItem(role=ItemRole.TEST_SUMMARY, content="\n".join(lines), token_estimate=500)
    result = compact_run_test(item)
    assert "FAILED" in result.content


def test_compaction_skips_non_test_items():
    item = ContextItem(role=ItemRole.ISSUE, content="\n".join(["x"] * 100), token_estimate=500)
    result = compact_run_test(item)
    assert result.meta.get("compacted") is None


def test_build_context_summary():
    pack = ContextPack(items=[
        ContextItem(role=ItemRole.ISSUE, content="issue"),
        ContextItem(role=ItemRole.TOOL_TRACE, content="long trace", token_estimate=5000, dropped=True, drop_reason="budget"),
    ])
    s = build_context_summary(pack)
    assert "total items: 2" in s
    assert "DROPPED" in s


def test_estimate_tokens():
    assert estimate_tokens("hello world") == 2
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100


def test_context_manager_default_build():
    cm = ContextManager()
    pack = cm.build_pack(issue="ISSUE TEXT", test_summary="ALL PASSED", tool_traces=["cmd1", "cmd2"])
    assert len(pack.items) == 4
    assert pack.items[0].role == ItemRole.ISSUE
    assert pack.items[1].role == ItemRole.TEST_SUMMARY
    assert pack.total_tokens > 0
