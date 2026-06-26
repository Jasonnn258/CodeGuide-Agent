from __future__ import annotations

import json

from codeguide_agent.context.manager import ContextManager
from codeguide_agent.rag.agent_loop import (
    HistoryRAGAgentLoop,
    HistoryRAGConfig,
    HistoryRAGContext,
    create_history_rag_loop,
)
from codeguide_agent.rag.history_index import ExperienceRecord, HistoryIndex


def _make_index_with_records() -> HistoryIndex:
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="task_A_gold",
        task_id="task_A",
        generator_family="parsing",
        patch_hash="ph_A",
        issue_pattern_hash="ih_A",
        split="train",
        retrieval_view={
            "issue_summary": "fix json parsing of nested objects",
            "failure_signal": "public_pass_hidden_fail",
            "patch_summary": "Changed 1 file(s): parser.py. +5/-2 lines.",
            "changed_files": ["parser.py"],
            "strategy": "sft: parsing — public_pass_hidden_fail",
        },
        storage_view={"gold_patch": "diff --git a/parser.py b/parser.py\n-old\n+new\n"},
    ))
    idx.add(ExperienceRecord(
        experience_id="task_B_gold",
        task_id="task_B",
        generator_family="sorting",
        patch_hash="ph_B",
        issue_pattern_hash="ih_B",
        split="train",
        retrieval_view={
            "issue_summary": "fix sort ordering for non-ascii strings",
            "failure_signal": "public_pass_hidden_fail",
            "patch_summary": "Changed 1 file(s): sorter.py. +3/-1 lines.",
            "changed_files": ["sorter.py"],
            "strategy": "sft: sorting — public_pass_hidden_fail",
        },
        storage_view={"gold_patch": "diff --git a/sorter.py b/sorter.py\n-old\n+new\n"},
    ))
    idx.add(ExperienceRecord(
        experience_id="task_C_gold",
        task_id="task_C",
        generator_family="parsing",
        patch_hash="ph_C",
        issue_pattern_hash="ih_C",
        split="train",
        retrieval_view={
            "issue_summary": "fix yaml config parsing crash",
            "failure_signal": "crash",
            "patch_summary": "Changed 1 file(s): config.py. +10/-0 lines.",
            "changed_files": ["config.py"],
            "strategy": "sft: parsing — crash",
        },
        storage_view={"gold_patch": "diff --git a/config.py b/config.py\n-old\n+new\n"},
    ))
    return idx


# ---------------------------------------------------------------------------
# disabled by default
# ---------------------------------------------------------------------------

def test_disabled_by_default():
    loop = create_history_rag_loop()
    assert loop.enabled is False

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )
    assert ctx.snippets == []
    assert ctx.retrieved_ids == []


def test_disabled_logs_event():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=False)
    loop._index = idx

    ctx = loop.build_history_context(task_id="task_A", issue_text="fix json", patch_hash="ph_A")
    assert ctx.snippets == []
    log = loop.get_safety_log()
    assert any(e["event"] == "history_rag_disabled" for e in log)


# ---------------------------------------------------------------------------
# enabled builds safe snippets
# ---------------------------------------------------------------------------

def test_enabled_builds_snippets():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing of nested objects",
        patch_hash="ph_A",
    )
    # Should retrieve task_C (parsing family, different patch_hash) but not task_A
    assert len(ctx.snippets) >= 1
    # task_A must be excluded
    assert "task_A_gold" not in ctx.retrieved_ids
    # task_B (sorting, unrelated) may or may not be retrieved
    # No leakage
    assert ctx.leakage_safe is True


def test_enabled_excludes_own_task():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing of nested objects",
        patch_hash="ph_A",
    )
    # Own task_id IS excluded and logged
    assert "task_A" in ctx.excluded_task_ids
    # Own experience must NOT appear in retrieved_ids
    assert "task_A_gold" not in ctx.retrieved_ids


# ---------------------------------------------------------------------------
# same-family warning guard
# ---------------------------------------------------------------------------

def test_same_family_warning_when_all_same():
    """When all retrieved records share the same family as the query task."""
    idx = HistoryIndex()
    # 5 records all in parsing family — query task_A + 4 others all "parsing"
    records = [
        ("t0", "task_A", "ph_A"),
        ("t1", "task_B", "ph_B"),
        ("t2", "task_C", "ph_C"),
        ("t3", "task_D", "ph_D"),
        ("t4", "task_E", "ph_E"),
    ]
    for exp_id, task_id, ph in records:
        idx.add(ExperienceRecord(
            experience_id=exp_id, task_id=task_id, generator_family="parsing", patch_hash=ph,
            issue_pattern_hash=f"ih_{exp_id}",
            retrieval_view={"issue_summary": f"fix {task_id} bug", "failure_signal": "crash",
                             "patch_summary": "fix", "changed_files": [f"{task_id}.py"], "strategy": "fix"},
            storage_view={"gold_patch": f"diff --git a/{task_id}.py b/{task_id}.py\n-old\n+new\n"},
        ))

    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )
    # Excluding task_A (t0), retrieved all 4 others — all "parsing" family >= threshold 3
    assert ctx.same_family_warning is True
    assert "parsing" in ctx.same_family_warning_detail


def test_no_family_warning_when_diverse():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )
    # task_B is sorting (different family), so warning should be False (max 3 threshold not met)
    assert ctx.same_family_warning is False


# ---------------------------------------------------------------------------
# snippet char cap enforcement
# ---------------------------------------------------------------------------

def test_snippet_char_cap():
    long_issue = "fix " + "very " * 200 + "long bug description"
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="t1", task_id="task_B", generator_family="parsing", patch_hash="ph_B",
        retrieval_view={
            "issue_summary": long_issue,
            "failure_signal": "crash " * 100,
            "patch_summary": "Changed 1 file(s): module.py. +1/-1 lines.",
            "changed_files": ["module.py"],
            "strategy": "fix it",
        },
    ))

    loop = create_history_rag_loop(enabled=True, max_chars_per_snippet=600)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix bug",
        patch_hash="ph_A",
    )
    for s in ctx.snippets:
        assert len(s["retrieval_text"]) <= 600, f"snippet too long: {len(s['retrieval_text'])}"


def test_max_snippets_cap():
    idx = HistoryIndex()
    for i in range(10):
        idx.add(ExperienceRecord(
            experience_id=f"t{i}", task_id=f"task_{i:03d}", generator_family=f"fam_{i%3}",
            patch_hash=f"ph_{i}",
            retrieval_view={
                "issue_summary": f"fix bug #{i}",
                "failure_signal": "crash",
                "patch_summary": "fix",
                "changed_files": [f"file_{i}.py"],
                "strategy": "fix",
            },
        ))

    loop = create_history_rag_loop(enabled=True, max_snippets=3)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_X",
        issue_text="fix bug",
        patch_hash="ph_X",
    )
    assert len(ctx.snippets) <= 3
    assert len(ctx.retrieved_ids) <= 3


# ---------------------------------------------------------------------------
# no leakage in agent-loop snippets
# ---------------------------------------------------------------------------

def test_no_full_diff_in_snippets():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )
    for s in ctx.snippets:
        text = s["retrieval_text"].lower()
        assert "diff --git" not in text
        assert "hidden_test" not in text
        assert "oracle" not in text
        assert "gold.patch" not in text


def test_no_forbidden_keys_in_snippet():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )
    for s in ctx.snippets:
        assert "gold_patch" not in s
        assert "full_diff" not in s
        assert "storage_view" not in s


# ---------------------------------------------------------------------------
# empty query handling
# ---------------------------------------------------------------------------

def test_empty_query_returns_empty():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(task_id="task_A", issue_text="", patch_hash="ph_A")
    assert ctx.snippets == []
    assert ctx.retrieved_ids == []


# ---------------------------------------------------------------------------
# ContextPack integration
# ---------------------------------------------------------------------------

def test_context_pack_integration():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    ctx = loop.build_history_context(
        task_id="task_A",
        issue_text="fix json parsing",
        patch_hash="ph_A",
    )

    cm = ContextManager()
    pack = cm.build_pack(
        issue="Fix the json parser",
        test_summary="3 passed",
        history_rag=ctx.to_context_pack_dicts(),
    )
    # Verify history items are in the pack
    history_items = [item for item in pack.items if item.role.value == "history_rag"]
    assert len(history_items) == len(ctx.snippets)

    # Verify no leakage in the pack
    from codeguide_agent.context.pack_builder import validate_no_leakage
    violations = validate_no_leakage(pack)
    assert violations == [], f"leakage in context pack: {violations}"


# ---------------------------------------------------------------------------
# safety report
# ---------------------------------------------------------------------------

def test_safety_report_tracks_events():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    loop.build_history_context(task_id="task_A", issue_text="fix json", patch_hash="ph_A")
    loop.build_history_context(task_id="task_B", issue_text="fix sort", patch_hash="ph_B")

    report = loop.get_safety_report()
    assert report["built_count"] == 2
    assert report["disabled_count"] == 0
    assert report["safe"] is True


def test_safety_log_clearable():
    idx = _make_index_with_records()
    loop = create_history_rag_loop(enabled=True)
    loop._index = idx

    loop.build_history_context(task_id="task_A", issue_text="fix json", patch_hash="ph_A")
    assert len(loop.get_safety_log()) > 0
    loop.clear_safety_log()
    assert len(loop.get_safety_log()) == 0


# ---------------------------------------------------------------------------
# HistoryRAGContext
# ---------------------------------------------------------------------------

def test_history_rag_context_defaults():
    ctx = HistoryRAGContext()
    assert ctx.snippets == []
    assert ctx.retrieved_ids == []
    assert ctx.same_family_warning is False
    assert ctx.leakage_safe is True
    assert ctx.total_available == 0


def test_history_rag_context_to_dicts():
    ctx = HistoryRAGContext(
        snippets=[
            {"retrieval_text": "Issue: fix bug | Fix: add check", "experience_id": "e1"},
        ],
        retrieved_ids=["e1"],
    )
    dicts = ctx.to_context_pack_dicts()
    assert len(dicts) == 1
    assert dicts[0]["retrieval_text"] == "Issue: fix bug | Fix: add check"
