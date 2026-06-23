from __future__ import annotations

import json

from codeguide_agent.rag.history_index import (
    ExperienceRecord,
    HistoryIndex,
    _simple_relevance,
    _summarize_patch,
    _truncate,
)


def test_experience_record_to_dict():
    rec = ExperienceRecord(
        experience_id="task_042_test",
        task_id="task_042",
        generator_family="path_handling",
        patch_hash="abc123",
        issue_pattern_hash="def456",
        storage_view={"gold_patch": "diff --git ..."},
        retrieval_view={
            "issue_summary": "path resolution bug",
            "failure_signal": "public passes, hidden fails",
            "patch_summary": "add path normalization",
            "changed_files": ["task_042_lib/paths.py"],
            "strategy": "normalize .. segments",
        },
    )
    d = rec.to_dict()
    assert d["experience_id"] == "task_042_test"
    assert d["task_id"] == "task_042"
    assert "diff --git" in d["storage_view"]["gold_patch"]
    assert "diff --git" not in json.dumps(d["retrieval_view"]).lower()


def test_history_index_add_and_retrieve():
    idx = HistoryIndex()
    rec = ExperienceRecord(
        experience_id="task_001_gold",
        task_id="task_001",
        generator_family="parsing",
        patch_hash="hash1",
        issue_pattern_hash="iph1",
        retrieval_view={
            "issue_summary": "fix json parsing of nested objects",
            "failure_signal": "public passes, hidden fails",
            "patch_summary": "add recursive key resolution",
            "changed_files": ["parser.py"],
            "strategy": "add nested lookup",
        },
    )
    idx.add(rec)
    results = idx.retrieve(query="json parsing of nested", top_k=5)
    assert len(results) == 1
    assert results[0].task_id == "task_001"


def test_history_index_excludes_task_id():
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="t1", task_id="task_001", generator_family="A",
        retrieval_view={"issue_summary": "bug A"},
    ))
    idx.add(ExperienceRecord(
        experience_id="t2", task_id="task_002", generator_family="B",
        retrieval_view={"issue_summary": "bug B"},
    ))
    results = idx.retrieve(query="bug", top_k=10, exclude_task_ids={"task_001"})
    ids = {r.task_id for r in results}
    assert "task_001" not in ids
    assert "task_002" in ids


def test_history_index_excludes_generator_family():
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="t1", task_id="task_001", generator_family="parsing",
        retrieval_view={"issue_summary": "parse"},
    ))
    idx.add(ExperienceRecord(
        experience_id="t2", task_id="task_002", generator_family="sorting",
        retrieval_view={"issue_summary": "sort"},
    ))
    results = idx.retrieve(query="", top_k=10, exclude_generator_families={"parsing"})
    families = {r.generator_family for r in results}
    assert "parsing" not in families
    assert "sorting" in families


def test_history_index_excludes_patch_hash():
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="t1", task_id="task_001", patch_hash="hash_A",
        retrieval_view={"issue_summary": "bug"},
    ))
    results = idx.retrieve(query="bug", top_k=10, exclude_patch_hashes={"hash_A"})
    assert len(results) == 0


def test_history_index_excludes_issue_pattern_hash():
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="t1", task_id="task_001", issue_pattern_hash="iph_X",
        retrieval_view={"issue_summary": "bug"},
    ))
    results = idx.retrieve(query="bug", top_k=10, exclude_issue_pattern_hashes={"iph_X"})
    assert len(results) == 0


def test_simple_relevance():
    assert _simple_relevance("json parsing", "fix json parsing bug in config") > 0
    assert _simple_relevance("", "something") == 0.0
    assert _simple_relevance("xyz", "abc def") == 0.0


def test_summarize_patch():
    patch = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 x = 1
+y = 2
-z = 3
"""
    s = _summarize_patch(patch)
    assert "foo.py" in s
    assert "+1" in s or "+1/" in s
    assert "-1" in s or "-1" in s


def test_truncate():
    assert _truncate("hello", 10) == "hello"
    assert _truncate("hello world this is long", 10) == "hello w..."


def test_history_index_save_and_load(tmp_path):
    idx = HistoryIndex()
    idx.add(ExperienceRecord(
        experience_id="e1", task_id="task_001",
        storage_view={"gold_patch": "diff --git a/x b/x"},
        retrieval_view={"issue_summary": "fix bug", "failure_signal": "crash", "patch_summary": "add check", "changed_files": ["x.py"], "strategy": "validate input"},
    ))
    path = tmp_path / "test_index.jsonl"
    idx.save(path)
    loaded = HistoryIndex.load(path)
    assert len(loaded.records) == 1
    assert loaded.records[0].task_id == "task_001"
    assert loaded.records[0].storage_view["gold_patch"] == "diff --git a/x b/x"
