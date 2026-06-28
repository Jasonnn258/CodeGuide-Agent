"""Tests for P1.7 Consolidated Offline Eval/Ablation Report.

Source: docs/ROADMAP_CONTEXT_RAG_TRAINING.md P1.7 — consolidate eval harness
(P1.5), dataset quality (P1.6), and RAG ablation outputs into a single local
offline report. JSON + Markdown. No training, no external APIs, no LLM calls,
no hidden/gold/oracle leakage in the report output.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from codeguide_agent.eval.consolidated_report import (
    ConsolidatedOfflineReport,
    SectionResult,
    build_consolidated_report,
    collect_agent_loop_ablation,
    collect_code_rag_localization,
    collect_history_rag_ablation,
    format_json,
    format_markdown,
)
from codeguide_agent.eval.harness_reporter import EvalHarnessReport
from codeguide_agent.eval.dataset_quality import DatasetQualityReport


# ---------------------------------------------------------------------------
# dataclass defaults
# ---------------------------------------------------------------------------


def test_section_result_defaults():
    s = SectionResult(name="x", available=True, passed=True)
    assert s.name == "x"
    assert s.available is True
    assert s.passed is True
    assert s.summary == ""
    assert s.details == {}


def test_consolidated_report_defaults():
    r = ConsolidatedOfflineReport()
    assert r.report_version == "1.0"
    assert r.overall_status == "unknown"
    assert r.sections == []
    assert r.eval_harness == {}
    assert r.dataset_quality == {}
    assert r.history_rag_ablation == {}
    assert r.code_rag_localization == {}
    assert r.agent_loop_ablation == {}


# ---------------------------------------------------------------------------
# collectors: missing-file graceful degradation
# ---------------------------------------------------------------------------


def test_collect_history_rag_ablation_missing(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    result = collect_history_rag_ablation(root)
    assert result["available"] is False
    assert "reason" in result


def test_collect_code_rag_localization_missing(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    result = collect_code_rag_localization(root)
    assert result["available"] is False
    assert "reason" in result


def test_collect_agent_loop_ablation_missing(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    result = collect_agent_loop_ablation(root)
    assert result["available"] is False
    assert "reason" in result


# ---------------------------------------------------------------------------
# collectors: read real JSON files
# ---------------------------------------------------------------------------


def test_collect_history_rag_ablation_reads_file(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    hist_dir = root / "history_index"
    hist_dir.mkdir(parents=True)
    data = {
        "modes": {
            "quality": {
                "passed": True,
                "leakage_safe": True,
                "family_hit_at_1": 0.75,
                "family_hit_at_3": 0.85,
                "family_hit_at_5": 0.90,
                "file_hit_at_1": 0.50,
                "file_hit_at_3": 0.70,
                "file_hit_at_5": 0.80,
                "total_queries": 100,
                "coverage_empty_pct": 5.0,
            },
        },
        "leakage": {"passed": True},
        "overall_passed": True,
        "total_records": 200,
        "unique_tasks": 100,
        "unique_families": 12,
    }
    (hist_dir / "ablation_results.json").write_text(json.dumps(data), encoding="utf-8")

    result = collect_history_rag_ablation(root)
    assert result["available"] is True
    assert result["overall_passed"] is True
    assert result["total_records"] == 200
    assert result["unique_tasks"] == 100
    assert result["unique_families"] == 12
    assert result["leakage_passed"] is True
    assert result["quality_mode"]["family_hit_at_1"] == 0.75
    assert result["quality_mode"]["passed"] is True


def test_collect_code_rag_localization_reads_file(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    code_dir = root / "code_index"
    code_dir.mkdir(parents=True)
    data = {
        "num_tasks": 100,
        "valid_tasks": 95,
        "avg_chunks_per_task": 12.3,
        "file_hit_at_1": 0.00,
        "file_hit_at_3": 0.10,
        "file_hit_at_5": 0.20,
        "symbol_hit_at_1": 0.42,
        "symbol_hit_at_3": 0.55,
        "symbol_hit_at_5": 0.68,
        "passed": True,
    }
    (code_dir / "localization_eval.json").write_text(json.dumps(data), encoding="utf-8")

    result = collect_code_rag_localization(root)
    assert result["available"] is True
    assert result["passed"] is True
    assert result["num_tasks"] == 100
    assert result["valid_tasks"] == 95
    assert result["symbol_hit_at_1"] == 0.42


def test_collect_agent_loop_ablation_reads_file(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    hist_dir = root / "history_index"
    hist_dir.mkdir(parents=True)
    data = {
        "disabled": {"total_tasks": 100, "total_snippets": 0, "leakage_safe": True},
        "enabled": {
            "total_tasks": 100,
            "total_snippets": 250,
            "avg_snippets_per_task": 2.5,
            "same_family_warnings": 0,
            "leakage_safe": True,
        },
        "overall_passed": True,
    }
    (hist_dir / "agent_loop_ablation.json").write_text(json.dumps(data), encoding="utf-8")

    result = collect_agent_loop_ablation(root)
    assert result["available"] is True
    assert result["overall_passed"] is True
    assert result["disabled"]["total_snippets"] == 0
    assert result["enabled"]["avg_snippets_per_task"] == 2.5
    assert result["enabled"]["leakage_safe"] is True


def test_collect_history_rag_ablation_handles_corrupt_json(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    hist_dir = root / "history_index"
    hist_dir.mkdir(parents=True)
    (hist_dir / "ablation_results.json").write_text("{not valid json", encoding="utf-8")
    result = collect_history_rag_ablation(root)
    assert result["available"] is False
    assert "reason" in result


# ---------------------------------------------------------------------------
# build_consolidated_report with mocked eval harness + dataset quality
# ---------------------------------------------------------------------------


def _mock_eval_harness_report(passed: bool = True) -> EvalHarnessReport:
    return EvalHarnessReport(
        generated_at="2026-01-01T00:00:00Z",
        branch="claude",
        commit="abc123456789",
        dataset_scale={
            "existing_task_dirs": 100,
            "sft_total": 100,
            "preference_total": 169,
            "preference_bank_total": 169,
            "hard_preference_total": 64,
            "training_readiness": {"task_count_ge_100": True},
        },
        p61_check={"passed": passed},
        wrapper_delegation={"passed": passed, "stdout": "OK: 6 wrappers"},
        swe_bench_smoke={"available": False, "reason": "no smoke data"},
        test_suite={"passed": passed, "test_count": 103},
        audit={"passed": passed, "stdout": "PASS"},
        clean_check={"passed": passed},
        compile_check={"passed": passed},
        overall_status="pass" if passed else "fail",
    )


def _mock_quality_report(passed: bool = True) -> DatasetQualityReport:
    return DatasetQualityReport(
        total_tasks=100,
        overall_status="pass" if passed else "fail",
        by_source={"handcrafted": 100},
        by_split={"train": 100},
        by_difficulty={"easy": 50, "medium": 50},
        by_bug_type={"parser_config": 50, "cache_state": 50},
        by_generator_family={"parsing": 100},
        flags={
            "template_leakage_risk_pair_count": 0,
            "history_index_available": True,
        },
    )


def _write_rag_outputs(root: Path, *, hist_pass=True, code_pass=True, agent_pass=True):
    hist_dir = root / "history_index"
    hist_dir.mkdir(parents=True, exist_ok=True)
    (hist_dir / "ablation_results.json").write_text(json.dumps({
        "modes": {"quality": {"passed": hist_pass, "leakage_safe": True,
                              "family_hit_at_1": 0.75, "total_queries": 100,
                              "coverage_empty_pct": 5.0}},
        "leakage": {"passed": hist_pass},
        "overall_passed": hist_pass,
        "total_records": 200, "unique_tasks": 100, "unique_families": 12,
    }), encoding="utf-8")
    (hist_dir / "agent_loop_ablation.json").write_text(json.dumps({
        "disabled": {"total_tasks": 100, "total_snippets": 0, "leakage_safe": True},
        "enabled": {"total_tasks": 100, "total_snippets": 250,
                    "avg_snippets_per_task": 2.5, "same_family_warnings": 0,
                    "leakage_safe": True},
        "overall_passed": agent_pass,
    }), encoding="utf-8")
    code_dir = root / "code_index"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "localization_eval.json").write_text(json.dumps({
        "num_tasks": 100, "valid_tasks": 95, "avg_chunks_per_task": 12.3,
        "symbol_hit_at_1": 0.42, "passed": code_pass,
    }), encoding="utf-8")


def test_build_consolidated_report_with_all_sections(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    _write_rag_outputs(root)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    section_names = {s.name for s in report.sections}
    assert section_names == {
        "eval_harness", "dataset_quality", "p61_check", "wrapper_delegation",
        "swe_bench_smoke", "history_rag_ablation", "code_rag_localization",
        "agent_loop_ablation",
    }
    assert report.overall_status == "pass"
    assert report.history_rag_ablation["available"] is True
    assert report.code_rag_localization["available"] is True
    assert report.agent_loop_ablation["available"] is True


def test_build_consolidated_report_passes_when_rag_missing(tmp_path: Path):
    """When RAG output files are absent, optional sections are skipped — overall still pass."""
    root = tmp_path / "mini_repo_debug"
    root.mkdir(parents=True)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    assert report.overall_status == "pass"
    assert report.history_rag_ablation["available"] is False
    assert report.code_rag_localization["available"] is False
    assert report.agent_loop_ablation["available"] is False


def test_build_consolidated_report_fails_when_eval_harness_fails(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    root.mkdir(parents=True)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=False)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    assert report.overall_status == "fail"


def test_build_consolidated_report_fails_when_quality_fails(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    root.mkdir(parents=True)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=False)
        report = build_consolidated_report(root=root)

    assert report.overall_status == "fail"


def test_build_consolidated_report_fails_when_optional_rag_fails(tmp_path: Path):
    """If a RAG ablation output exists and reports failure, overall report fails."""
    root = tmp_path / "mini_repo_debug"
    _write_rag_outputs(root, hist_pass=False, code_pass=True, agent_pass=True)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    assert report.overall_status == "fail"
    assert report.history_rag_ablation["overall_passed"] is False


# ---------------------------------------------------------------------------
# formatters
# ---------------------------------------------------------------------------


def test_format_json_has_required_keys(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    _write_rag_outputs(root)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    text = format_json(report)
    data = json.loads(text)
    for key in (
        "report_version", "generated_at", "branch", "commit", "overall_status",
        "eval_harness", "dataset_quality", "p61_check", "wrapper_delegation",
        "swe_bench_smoke", "history_rag_ablation", "code_rag_localization",
        "agent_loop_ablation", "sections",
    ):
        assert key in data, f"missing key: {key}"
    assert data["overall_status"] == "pass"
    assert len(data["sections"]) == 8


def test_format_markdown_has_sections(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    _write_rag_outputs(root)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    text = format_markdown(report)
    assert "# CodeGuide-Agent Consolidated Offline Report" in text
    assert "## Sections" in text
    for name in (
        "eval_harness", "dataset_quality", "p61_check", "wrapper_delegation",
        "swe_bench_smoke", "history_rag_ablation", "code_rag_localization",
        "agent_loop_ablation",
    ):
        assert name in text, f"missing section name in markdown: {name}"
    assert "PASS" in text


def test_format_markdown_fail_status(tmp_path: Path):
    root = tmp_path / "mini_repo_debug"
    root.mkdir(parents=True)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=False)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    text = format_markdown(report)
    assert "FAIL" in text


# ---------------------------------------------------------------------------
# leakage safety: report must not contain gold/hidden content
# ---------------------------------------------------------------------------


def test_report_does_not_leak_gold_or_hidden_content(tmp_path: Path):
    """The consolidated report must not surface full diffs, hidden test content,
    or oracle identifiers. Only summary metadata is allowed.
    """
    root = tmp_path / "mini_repo_debug"
    _write_rag_outputs(root)
    with patch("codeguide_agent.eval.consolidated_report._build_harness_report") as mh, \
         patch("codeguide_agent.eval.consolidated_report._build_quality_report") as mq:
        mh.return_value = _mock_eval_harness_report(passed=True)
        mq.return_value = _mock_quality_report(passed=True)
        report = build_consolidated_report(root=root)

    text = format_json(report) + "\n" + format_markdown(report)
    forbidden = ["diff --git", "gold.patch", "tests_hidden", "hidden_test", "oracle"]
    for term in forbidden:
        assert term not in text, f"leakage: '{term}' in report output"


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_help():
    proc = subprocess.run(
        ["python", "scripts/run_consolidated_offline_report.py", "--help"],
        capture_output=True, text=True, timeout=30,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=False,
    )
    assert proc.returncode == 0
    assert "--json" in proc.stdout
    assert "--markdown" in proc.stdout


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
