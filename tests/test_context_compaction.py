from __future__ import annotations

from codeguide_agent.context.compaction import _is_failure_line, compact_run_test
from codeguide_agent.context.schemas import ContextItem, ItemRole


def test_is_failure_line_detects_fail():
    assert _is_failure_line("FAILED test_foo") is True
    assert _is_failure_line("AssertionError") is True
    assert _is_failure_line("Traceback (most recent call last):") is True


def test_is_failure_line_ignores_normal():
    assert _is_failure_line("test_foo PASSED") is False
    assert _is_failure_line("collected 42 items") is False


def test_compaction_preserves_header_and_tail():
    lines = ["HEADER-{}".format(i) for i in range(50)]
    lines += ["routine output"] * 100
    lines += ["TAIL-{}".format(i) for i in range(50)]
    item = ContextItem(role=ItemRole.TEST_SUMMARY, content="\n".join(lines), token_estimate=1000)
    result = compact_run_test(item)
    assert "HEADER-0" in result.content
    assert "TAIL-49" in result.content
    assert result.meta["compacted"] is True


def test_compaction_keeps_short_output_intact():
    short = "\n".join(["line"] * 10)
    item = ContextItem(role=ItemRole.TEST_SUMMARY, content=short, token_estimate=10)
    result = compact_run_test(item)
    assert result.content == short
    assert result.meta.get("compacted") is None
