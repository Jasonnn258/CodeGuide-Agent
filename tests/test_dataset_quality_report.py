from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from codeguide_agent.eval.dataset_quality import (
    REQUIRED_METADATA_FIELDS,
    build_quality_report,
    format_json,
    format_markdown,
)


def _write_metadata(task_dir: Path, task_id: str, *, source: str = "handcrafted",
                    bug_type: str = "parser_config", difficulty: str = "easy",
                    gold_files=None, gold_functions=None) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "src").mkdir(exist_ok=True)
    (task_dir / "tests").mkdir(exist_ok=True)
    (task_dir / "tests_hidden").mkdir(exist_ok=True)
    (task_dir / "issue.md").write_text("# issue\n", encoding="utf-8")
    (task_dir / "gold.patch").write_text("diff --git a/x b/x\n-old\n+new\n", encoding="utf-8")
    meta = {
        "task_id": task_id,
        "bug_type": bug_type,
        "scenario": "auto_repair",
        "difficulty": difficulty,
        "repo_path": str(task_dir),
        "issue_path": "issue.md",
        "gold_files": gold_files or ["src/lib.py"],
        "gold_functions": gold_functions or ["load_config"],
        "gold_patch": "gold.patch",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "forbidden_behaviors": ["delete_tests"],
        "source": source,
        "split": "train",
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_experience(history_path: Path, exp_id: str, task_id: str, *,
                      family: str = "parsing", patch_hash: str = "",
                      issue_pattern_hash: str = "") -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "experience_id": exp_id,
        "task_id": task_id,
        "split": "train",
        "generator_family": family,
        "patch_hash": patch_hash or f"ph_{task_id}",
        "issue_pattern_hash": issue_pattern_hash or f"ih_{task_id}",
        "storage_view": {"gold_patch": "diff --git a/x b/x\n-old\n+new\n", "negative_rollouts": []},
        "retrieval_view": {
            "issue_summary": "issue",
            "failure_signal": "public_passes",
            "patch_summary": "patch",
            "changed_files": ["src/lib.py"],
            "strategy": "sft: parsing",
        },
        "visibility": {"allow_in_training": True, "allow_full_diff_in_retrieval_prompt": False},
    }
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_report_passes_with_complete_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")
        _write_metadata(repos / "task_002", "task_002", bug_type="cache_state")

        report = build_quality_report(root=root)
        assert report.total_tasks == 2
        assert report.overall_status == "pass"
        assert report.by_source.get("handcrafted") == 2
        assert report.by_bug_type.get("parser_config") == 1
        assert report.by_bug_type.get("cache_state") == 1


def test_report_fails_when_required_metadata_missing():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        (repos / "task_001").mkdir(parents=True)
        (repos / "task_001" / "src").mkdir()
        (repos / "task_001" / "tests").mkdir()
        (repos / "task_001" / "tests_hidden").mkdir()
        (repos / "task_001" / "issue.md").write_text("x", encoding="utf-8")
        (repos / "task_001" / "gold.patch").write_text("x", encoding="utf-8")
        meta = {"task_id": "task_001", "bug_type": "parser_config", "source": "handcrafted", "split": "train"}
        (repos / "task_001" / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        report = build_quality_report(root=root)
        assert report.total_tasks == 1
        assert report.overall_status == "fail"
        missing = report.metadata_completeness["missing_field_counts"]
        assert missing.get("gold_files") == 1
        assert missing.get("gold_functions") == 1


def test_patch_hash_duplicates_flagged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")
        _write_metadata(repos / "task_002", "task_002", bug_type="cache_state")
        history = root / "history_index" / "experience_records.jsonl"
        _write_experience(history, "task_001_gold_reference", "task_001", family="parsing", patch_hash="DUPE_HASH")
        _write_experience(history, "task_002_gold_reference", "task_002", family="parsing", patch_hash="DUPE_HASH")

        report = build_quality_report(root=root)
        assert "DUPE_HASH" in report.patch_hash_duplicates
        assert set(report.patch_hash_duplicates["DUPE_HASH"]) == {"task_001", "task_002"}
        assert report.flags["patch_hash_duplicate_groups"] == 1


def test_issue_pattern_hash_duplicates_flagged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")
        _write_metadata(repos / "task_002", "task_002", bug_type="cache_state")
        history = root / "history_index" / "experience_records.jsonl"
        _write_experience(history, "task_001_gold_reference", "task_001",
                          family="parsing", issue_pattern_hash="DUPE_ISSUE")
        _write_experience(history, "task_002_gold_reference", "task_002",
                          family="parsing", issue_pattern_hash="DUPE_ISSUE")

        report = build_quality_report(root=root)
        assert "DUPE_ISSUE" in report.issue_pattern_hash_duplicates
        assert set(report.issue_pattern_hash_duplicates["DUPE_ISSUE"]) == {"task_001", "task_002"}


def test_template_leakage_risk_pair_detected():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")
        _write_metadata(repos / "task_002", "task_002", bug_type="cache_state")
        history = root / "history_index" / "experience_records.jsonl"
        _write_experience(history, "task_001_gold_reference", "task_001",
                          family="parsing", patch_hash="hash_a", issue_pattern_hash="SHARED_IPH")
        _write_experience(history, "task_002_gold_reference", "task_002",
                          family="parsing", patch_hash="hash_b", issue_pattern_hash="SHARED_IPH")

        report = build_quality_report(root=root)
        assert len(report.template_leakage_risk_pairs) == 1
        pair = report.template_leakage_risk_pairs[0]
        assert pair["task_a"] == "task_001"
        assert pair["task_b"] == "task_002"
        assert pair["generator_family"] == "parsing"
        assert pair["shared_issue_pattern_hash"] is True
        assert pair["shared_patch_hash"] is False


def test_no_template_leakage_when_only_family_matches():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")
        _write_metadata(repos / "task_002", "task_002", bug_type="cache_state")
        history = root / "history_index" / "experience_records.jsonl"
        _write_experience(history, "task_001_gold_reference", "task_001",
                          family="parsing", patch_hash="hash_a", issue_pattern_hash="iph_a")
        _write_experience(history, "task_002_gold_reference", "task_002",
                          family="parsing", patch_hash="hash_b", issue_pattern_hash="iph_b")

        report = build_quality_report(root=root)
        assert report.template_leakage_risk_pairs == []
        assert report.flags["template_leakage_risk_pair_count"] == 0


def test_gold_functions_overlap_groups():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001", gold_functions=["load_config"])
        _write_metadata(repos / "task_002", "task_002", gold_functions=["load_config"])
        _write_metadata(repos / "task_003", "task_003", gold_functions=["other_fn"])

        report = build_quality_report(root=root)
        groups = report.gold_functions_overlap_groups
        load_config_group = next(g for g in groups if g["gold_functions"] == ["load_config"])
        assert set(load_config_group["task_ids"]) == {"task_001", "task_002"}
        assert report.flags["gold_functions_overlap_groups"] == 1


def test_required_metadata_fields_complete():
    expected = {
        "task_id", "bug_type", "scenario", "difficulty", "repo_path", "source", "split",
        "gold_files", "gold_functions", "gold_patch", "public_test_cmd", "hidden_test_cmd",
    }
    assert set(REQUIRED_METADATA_FIELDS) == expected


def test_format_json_and_markdown_run():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mini_repo_debug"
        repos = root / "repos"
        _write_metadata(repos / "task_001", "task_001")

        report = build_quality_report(root=root)
        j = format_json(report)
        md = format_markdown(report)
        assert '"total_tasks": 1' in j
        assert "Dataset Quality Report" in md
        parsed = json.loads(j)
        assert parsed["total_tasks"] == 1


if __name__ == "__main__":
    import sys
    funcs = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
