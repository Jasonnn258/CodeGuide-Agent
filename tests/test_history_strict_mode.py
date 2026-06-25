from __future__ import annotations

import json

from codeguide_agent.rag.history_index import (
    ExperienceRecord,
    HistoryIndex,
    _deterministic_sort,
    _multi_field_score,
)


def _make_rec(
    exp_id: str,
    task_id: str,
    family: str = "parsing",
    patch_hash: str = "",
    issue_pattern_hash: str = "",
    split: str = "train",
    issue_summary: str = "fix parsing bug",
    changed_files: list[str] | None = None,
    failure_signal: str = "crash",
    patch_summary: str = "add check",
    strategy: str = "fix parsing logic",
) -> ExperienceRecord:
    return ExperienceRecord(
        experience_id=exp_id,
        task_id=task_id,
        generator_family=family,
        patch_hash=patch_hash or f"ph_{exp_id}",
        issue_pattern_hash=issue_pattern_hash or f"ih_{exp_id}",
        split=split,
        retrieval_view={
            "issue_summary": issue_summary,
            "failure_signal": failure_signal,
            "patch_summary": patch_summary,
            "changed_files": changed_files or [f"{task_id}_lib/module.py"],
            "strategy": strategy,
        },
        storage_view={"gold_patch": "diff --git a/x b/x\n-old\n+new\n"},
    )


# ---------------------------------------------------------------------------
# strict-mode exclusion
# ---------------------------------------------------------------------------

def test_strict_mode_excludes_all_five_dimensions():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="parsing", patch_hash="ph1", issue_pattern_hash="ih1", split="train"))
    idx.add(_make_rec("e2", "task_B", family="sorting", patch_hash="ph2", issue_pattern_hash="ih2", split="eval"))
    idx.add(_make_rec("e3", "task_C", family="parsing", patch_hash="ph3", issue_pattern_hash="ih3", split="train"))
    idx.add(_make_rec("e4", "task_D", family="filtering", patch_hash="ph4", issue_pattern_hash="ih4", split="train"))

    results = idx.retrieve_strict(
        query="fix bug",
        top_k=10,
        exclude_task_ids={"task_A"},
        exclude_generator_families={"parsing"},
        exclude_patch_hashes={"ph2"},
        exclude_issue_pattern_hashes={"ih4"},
        exclude_splits={"eval"},
    )
    ids = {r.task_id for r in results}
    assert "task_A" not in ids  # excluded by task_id
    assert "task_C" not in ids  # excluded by generator_family
    assert "task_B" not in ids  # excluded by patch_hash + split
    assert "task_D" not in ids  # excluded by issue_pattern_hash


def test_strict_mode_returns_empty_when_all_excluded():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="A", patch_hash="ph1"))
    idx.add(_make_rec("e2", "task_B", family="A", patch_hash="ph2"))

    results = idx.retrieve_strict(
        query="fix bug", top_k=10,
        exclude_task_ids={"task_A", "task_B"},
        exclude_generator_families={"A"},
    )
    assert len(results) == 0


# ---------------------------------------------------------------------------
# quality mode
# ---------------------------------------------------------------------------

def test_quality_mode_only_excludes_task_and_patch_hash():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="parsing", patch_hash="ph1", issue_pattern_hash="ih1"))
    idx.add(_make_rec("e2", "task_B", family="parsing", patch_hash="ph2", issue_pattern_hash="ih2"))
    idx.add(_make_rec("e3", "task_C", family="sorting", patch_hash="ph3", issue_pattern_hash="ih3"))

    results = idx.retrieve_quality(
        query="fix parsing bug",
        top_k=10,
        exclude_task_ids={"task_A"},
        exclude_patch_hashes={"ph1"},
    )
    ids = {r.task_id for r in results}
    assert "task_A" not in ids  # excluded by task_id
    # task_B should be included (same family, different patch_hash)
    assert "task_B" in ids
    # task_C may be included (different family)


# ---------------------------------------------------------------------------
# coverage (not silently empty)
# ---------------------------------------------------------------------------

def test_get_coverage_counts_remaining():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="A"))
    idx.add(_make_rec("e2", "task_B", family="A"))
    idx.add(_make_rec("e3", "task_C", family="B"))

    assert idx.get_coverage() == 3
    assert idx.get_coverage(exclude_task_ids={"task_A"}) == 2
    assert idx.get_coverage(exclude_task_ids={"task_A"}, exclude_generator_families={"A"}) == 1
    assert idx.get_coverage(exclude_task_ids={"task_A", "task_B", "task_C"}) == 0


def test_coverage_zero_means_silently_empty():
    """When coverage is 0, retrieval must return [] — this is the guard test."""
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="A"))

    cov = idx.get_coverage(exclude_task_ids={"task_A"}, exclude_generator_families={"A"})
    assert cov == 0

    results = idx.retrieve_strict(
        query="fix bug",
        top_k=5,
        exclude_task_ids={"task_A"},
        exclude_generator_families={"A"},
    )
    assert results == []


# ---------------------------------------------------------------------------
# deterministic scoring
# ---------------------------------------------------------------------------

def test_multi_field_score_is_deterministic():
    rec = _make_rec("e1", "task_A", issue_summary="fix json parsing of nested objects")
    s1 = _multi_field_score("json parsing nested", rec)
    s2 = _multi_field_score("json parsing nested", rec)
    assert s1 == s2
    assert s1 > 0


def test_multi_field_score_zero_for_no_match():
    rec = _make_rec("e1", "task_A", issue_summary="fix sorting", failure_signal="crash",
                     patch_summary="add sort", strategy="sort items")
    score = _multi_field_score("xyz abc def", rec)
    # Should be 0 or very close to 0 with no term overlap
    assert score == 0.0


def test_deterministic_sort_tie_breaks_by_experience_id():
    rec_a = _make_rec("rec_a", "task_001", issue_summary="fix bug")
    rec_b = _make_rec("rec_b", "task_002", issue_summary="fix bug")
    rec_c = _make_rec("rec_c", "task_003", issue_summary="fix bug")
    # All same score
    candidates = [(0.5, rec_c), (0.5, rec_a), (0.5, rec_b)]
    sorted_cands = _deterministic_sort(candidates)
    ids = [c[1].experience_id for c in sorted_cands]
    assert ids == ["rec_a", "rec_b", "rec_c"]


# ---------------------------------------------------------------------------
# retrieval_view leakage safety in both modes
# ---------------------------------------------------------------------------

def test_retrieval_view_no_leakage_in_quality_mode():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", issue_summary="fix parsing", changed_files=["parser.py"]))
    idx.add(_make_rec("e2", "task_B", issue_summary="fix sorting", changed_files=["sorter.py"]))

    results = idx.retrieve_quality(query="fix parsing", top_k=5,
                                    exclude_task_ids={"task_A"}, exclude_patch_hashes={"ph_e1"})
    for r in results:
        rv = json.dumps(r.retrieval_view).lower()
        assert "diff --git" not in rv
        assert "hidden_test" not in rv
        assert "oracle" not in rv


def test_retrieval_view_no_leakage_in_strict_mode():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="X", issue_summary="fix parsing"))
    idx.add(_make_rec("e2", "task_B", family="Y", issue_summary="fix sorting"))

    results = idx.retrieve_strict(query="fix parsing", top_k=5,
                                   exclude_task_ids={"task_A"},
                                   exclude_generator_families={"X"},
                                   exclude_patch_hashes={"ph_e1"},
                                   exclude_issue_pattern_hashes={"ih_e1"},
                                   exclude_splits={"train"})
    # With task_A and family X excluded, plus split=train excluded, should be empty
    for r in results:
        rv = json.dumps(r.retrieval_view).lower()
        assert "diff --git" not in rv


# ---------------------------------------------------------------------------
# property accessors
# ---------------------------------------------------------------------------

def test_index_properties():
    idx = HistoryIndex()
    idx.add(_make_rec("e1", "task_A", family="parsing", patch_hash="ph1", issue_pattern_hash="ih1", split="train"))
    idx.add(_make_rec("e2", "task_B", family="sorting", patch_hash="ph2", issue_pattern_hash="ih2", split="eval"))

    assert idx.task_ids == {"task_A", "task_B"}
    assert idx.generator_families == {"parsing", "sorting"}
    assert idx.patch_hashes == {"ph1", "ph2"}
    assert idx.issue_pattern_hashes == {"ih1", "ih2"}
    assert idx.splits == {"train", "eval"}


# ---------------------------------------------------------------------------
# ablation: coverage not silently empty
# ---------------------------------------------------------------------------

def test_quality_mode_has_better_coverage_than_strict():
    """Quality mode should return >= results than strict mode."""
    idx = HistoryIndex()
    # Same family — strict will exclude them, quality won't
    idx.add(_make_rec("e1", "task_A", family="parsing", patch_hash="ph1", issue_summary="fix json parsing bug"))
    idx.add(_make_rec("e2", "task_B", family="parsing", patch_hash="ph2", issue_summary="fix yaml parsing bug"))
    idx.add(_make_rec("e3", "task_C", family="sorting", patch_hash="ph3", issue_summary="fix sort order"))

    quality = idx.retrieve_quality(
        query="fix parsing bug",
        top_k=10,
        exclude_task_ids={"task_A"},
        exclude_patch_hashes={"ph1"},
    )
    strict = idx.retrieve_strict(
        query="fix parsing bug",
        top_k=10,
        exclude_task_ids={"task_A"},
        exclude_generator_families={"parsing"},
        exclude_patch_hashes={"ph1"},
        exclude_issue_pattern_hashes={"ih_e1"},
        exclude_splits={"train"},
    )
    assert len(quality) >= len(strict)
