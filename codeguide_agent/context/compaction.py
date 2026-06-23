from __future__ import annotations

import re

from codeguide_agent.context.schemas import ContextItem, ItemRole

_MAX_RUN_TEST_LINES = 30
_FAILURE_SIGNAL_KEEP = 8


def compact_run_test(item: ContextItem) -> ContextItem:
    """Compress long test-run logs: keep header, tail, and failure sections."""
    if item.role != ItemRole.TEST_SUMMARY:
        return item
    lines = item.content.split("\n")
    if len(lines) <= _MAX_RUN_TEST_LINES:
        return item
    # keep first few and last few lines
    head = lines[:_MAX_RUN_TEST_LINES // 2]
    tail = lines[-(_MAX_RUN_TEST_LINES // 2):]
    # also capture any failure blocks
    failure_lines = [
        line
        for line in lines[_MAX_RUN_TEST_LINES // 2 : -( _MAX_RUN_TEST_LINES // 2)]
        if _is_failure_line(line)
    ]
    if failure_lines:
        middle = ["... [failure signal preserved] ..."] + failure_lines[-_FAILURE_SIGNAL_KEEP:]
    else:
        middle = ["... [truncated] ..."]
    item.content = "\n".join(head + middle + tail)
    item.meta["compacted"] = True
    item.meta["original_lines"] = len(lines)
    item.token_estimate = max(1, len(item.content) // 4)
    return item


def _is_failure_line(line: str) -> bool:
    return bool(
        re.search(r"(?i)(FAILED|Error|Traceback|AssertionError|assert\b|\bFAIL\b)", line)
    )
