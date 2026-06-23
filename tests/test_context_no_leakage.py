from __future__ import annotations

from codeguide_agent.context.manager import ContextManager
from codeguide_agent.context.pack_builder import validate_no_leakage


def test_no_forbidden_content_in_pack():
    cm = ContextManager()
    pack = cm.build_pack(
        issue="Fix the API endpoint",
        test_summary="3 tests passed, 0 failed",
        files={"api.py": "def handler(): return 200"},
        tool_traces=["$ pytest tests -q"],
    )
    violations = validate_no_leakage(pack)
    assert violations == [], f"unexpected leakage: {violations}"


def test_leakage_detected_when_present():
    cm = ContextManager()
    pack = cm.build_pack(
        issue="Fix the bug",
        test_summary="gold.patch applied",
    )
    violations = validate_no_leakage(pack)
    assert len(violations) > 0


def test_leakage_detects_hidden_tests():
    cm = ContextManager()
    pack = cm.build_pack(
        issue="Fix the bug",
        test_summary="hidden_test shows the edge case",
    )
    violations = validate_no_leakage(pack)
    assert len(violations) > 0


def test_no_leakage_in_normal_issue():
    cm = ContextManager()
    pack = cm.build_pack(
        issue="Parse version strings with pre-release suffixes",
        test_summary="2 passed",
    )
    violations = validate_no_leakage(pack)
    assert violations == []
