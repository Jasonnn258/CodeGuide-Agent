from __future__ import annotations

import json

from codeguide_agent.rag.history_index import ExperienceRecord, HistoryIndex


def test_retrieval_view_excludes_full_diff():
    rec = ExperienceRecord(
        experience_id="test_leak",
        task_id="task_001",
        storage_view={"gold_patch": "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new\n"},
        retrieval_view={
            "issue_summary": "fix parsing",
            "failure_signal": "public pass, hidden fail",
            "patch_summary": "Changed 1 file(s): a/foo.py, b/foo.py. +1/-1 lines.",
            "changed_files": ["foo.py"],
            "strategy": "fix parsing logic",
        },
    )
    rv_json = json.dumps(rec.retrieval_view).lower()
    assert "diff --git" not in rv_json
    assert "--- a/" not in rv_json
    assert "+++ b/" not in rv_json


def test_retrieval_view_excludes_hidden_test_references():
    rec = ExperienceRecord(
        experience_id="test_hidden_leak",
        task_id="task_002",
        retrieval_view={
            "issue_summary": "fix email validation",
            "failure_signal": "public pass, hidden fail on edge case",
            "patch_summary": "add positional constraint checks",
            "changed_files": ["email_check.py"],
            "strategy": "validate @ position and dot position",
        },
    )
    rv_json = json.dumps(rec.retrieval_view).lower()
    assert "hidden_test" not in rv_json
    assert "tests_hidden" not in rv_json
    assert "gold.patch" not in rv_json


def test_retrieval_view_has_no_forbidden_keys():
    rec = ExperienceRecord(
        experience_id="test_keys",
        task_id="task_003",
        retrieval_view={
            "issue_summary": "fix bug",
            "failure_signal": "crash",
            "patch_summary": "fix",
            "changed_files": ["x.py"],
            "strategy": "fix",
        },
    )
    forbidden = {"gold_patch", "hidden_test", "oracle_action", "evaluator_stuff"}
    keys = set(rec.retrieval_view.keys())
    assert keys.isdisjoint(forbidden)


def test_index_retrieve_respects_all_exclusions():
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="e1", task_id="task_A", generator_family="G1",
        patch_hash="ph1", issue_pattern_hash="ih1", split="train",
        retrieval_view={"issue_summary": "fix bug A"},
    ))
    idx.add(ExperienceRecord(
        experience_id="e2", task_id="task_B", generator_family="G2",
        patch_hash="ph2", issue_pattern_hash="ih2", split="eval",
        retrieval_view={"issue_summary": "fix bug B"},
    ))
    idx.add(ExperienceRecord(
        experience_id="e3", task_id="task_C", generator_family="G1",
        patch_hash="ph3", issue_pattern_hash="ih3", split="train",
        retrieval_view={"issue_summary": "fix bug C"},
    ))

    results = idx.retrieve(
        query="fix bug",
        top_k=10,
        exclude_task_ids={"task_A"},
        exclude_generator_families={"G1"},
        exclude_patch_hashes={"ph2"},
        exclude_splits={"eval"},
    )
    task_ids = {r.task_id for r in results}
    assert "task_A" not in task_ids
    assert "task_C" not in task_ids  # excluded by generator_family
    assert "task_B" not in task_ids  # excluded by patch_hash and split
