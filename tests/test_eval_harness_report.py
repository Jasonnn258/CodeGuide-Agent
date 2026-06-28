"""Tests for P1.5 eval harness reporter."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from codeguide_agent.eval.harness_reporter import (
    CheckResult,
    EvalHarnessReport,
    _compact,
    _parse_pytest_count,
    _tail,
    build_report,
    collect_dataset_scale,
    collect_git_info,
    collect_swe_bench_smoke,
    format_json,
    format_markdown,
)


# ---------------------------------------------------------------------------
# data structure tests
# ---------------------------------------------------------------------------


def test_check_result_defaults():
    c = CheckResult(name="test", passed=True)
    assert c.name == "test"
    assert c.passed is True
    assert c.details == {}
    assert c.error == ""


def test_eval_harness_report_defaults():
    r = EvalHarnessReport()
    assert r.report_version == "1.0"
    assert r.overall_status == "unknown"
    assert r.dataset_scale == {}
    assert r.checks == []


# ---------------------------------------------------------------------------
# helper tests
# ---------------------------------------------------------------------------


def test_tail_short():
    assert _tail("line1", 5) == "line1"


def test_tail_long():
    text = "\n".join(f"line{i}" for i in range(10))
    result = _tail(text, 3)
    assert result == "line7\nline8\nline9"


def test_parse_pytest_count():
    assert _parse_pytest_count("198 passed") == 198
    assert _parse_pytest_count("0 passed") == 0
    assert _parse_pytest_count("no tests") == 0


def test_compact_drops_stdout_on_pass():
    d = {"passed": True, "stdout_tail": "big output", "stderr_tail": "err", "value": 42}
    c = _compact(d)
    assert "stdout_tail" not in c
    assert "stderr_tail" not in c
    assert c["value"] == 42


def test_compact_keeps_stdout_on_fail():
    d = {"passed": False, "stdout_tail": "error output", "value": 42}
    c = _compact(d)
    assert "stdout_tail" in c


# ---------------------------------------------------------------------------
# JSON formatting tests
# ---------------------------------------------------------------------------


def test_json_output_has_required_keys():
    report = EvalHarnessReport(
        generated_at="2026-01-01T00:00:00Z",
        branch="claude",
        commit="abc123",
        dataset_scale={"existing_task_dirs": 100},
        p61_check={"passed": True},
        wrapper_delegation={"passed": True},
        swe_bench_smoke={"available": True, "passed": True, "total": 5},
        test_suite={"passed": True, "test_count": 198},
        audit={"passed": True},
        clean_check={"passed": True, "test_count": 198},
        compile_check={"passed": True},
        checks=[
            CheckResult(name="test_suite", passed=True, details={"test_count": 198}),
        ],
        overall_status="pass",
    )
    text = format_json(report)
    data = json.loads(text)

    for key in (
        "report_version", "generated_at", "branch", "commit", "overall_status",
        "dataset_scale", "p61_check", "wrapper_delegation", "swe_bench_smoke",
        "test_suite", "audit", "clean_check", "compile_check", "checks",
    ):
        assert key in data, f"missing key: {key}"

    assert data["overall_status"] == "pass"
    assert data["dataset_scale"]["existing_task_dirs"] == 100


def test_json_checks_are_serialized():
    report = EvalHarnessReport(
        checks=[
            CheckResult(name="audit", passed=True, details={"stdout": "PASS"}),
            CheckResult(name="compile", passed=False, details={}, error="import error"),
        ],
    )
    text = format_json(report)
    data = json.loads(text)
    assert len(data["checks"]) == 2
    assert data["checks"][0]["name"] == "audit"
    assert data["checks"][1]["passed"] is False


# ---------------------------------------------------------------------------
# Markdown formatting tests
# ---------------------------------------------------------------------------


def test_markdown_output_has_sections():
    report = EvalHarnessReport(
        generated_at="2026-01-01T00:00:00Z",
        branch="claude",
        commit="abc123456789",
        dataset_scale={"existing_task_dirs": 100, "sft_total": 100},
        overall_status="pass",
        swe_bench_smoke={"available": False, "reason": "no data"},
        wrapper_delegation={"stdout": "OK: 6 wrappers"},
        audit={"stdout": "PASS"},
        checks=[
            CheckResult(name="test_suite", passed=True, details={"test_count": 198}),
        ],
    )
    text = format_markdown(report)

    assert "# CodeGuide-Agent Eval Harness Report" in text
    assert "**Overall**: PASS" in text
    assert "`claude`" in text
    assert "`abc123456789`" in text
    assert "## Dataset Scale" in text
    assert "## Checks" in text
    assert "## SWE-bench Smoke" in text
    assert "## Raw Output" in text
    assert "OK: 6 wrappers" in text
    assert "PASS" in text


def test_markdown_handles_fail_status():
    report = EvalHarnessReport(overall_status="fail", checks=[
        CheckResult(name="audit", passed=False, details={}),
    ])
    text = format_markdown(report)
    assert "**Overall**: FAIL" in text
    assert "FAIL" in text


def test_markdown_swe_bench_smoke_available():
    report = EvalHarnessReport(
        swe_bench_smoke={
            "available": True, "passed": True, "total": 5, "resolved": 5,
            "resolve_rate": 1.0, "all_gold_resolved": True, "all_empty_unresolved": True,
        },
    )
    text = format_markdown(report)
    assert "total: 5" in text
    assert "resolved: 5" in text


# ---------------------------------------------------------------------------
# collection tests (mock subprocess)
# ---------------------------------------------------------------------------


def test_collect_git_info_mocked():
    responses = iter(["claude", "abc123"])

    def fake_git(*_args: str) -> str:
        return next(responses)

    with patch("codeguide_agent.eval.harness_reporter._git", side_effect=fake_git):
        branch, commit = collect_git_info()
    assert branch == "claude"
    assert commit == "abc123"


def test_collect_dataset_scale_returns_expected_keys(tmp_path: Path):
    # Create a minimal dataset root
    root = tmp_path / "mini_repo"
    (root / "repos").mkdir(parents=True)
    (root / "train_package").mkdir(parents=True)
    (root / "preference_bank").mkdir(parents=True)

    # Empty JSONL files
    for p in ["sft_train.jsonl", "sft_eval.jsonl", "preference_train.jsonl", "preference_eval.jsonl"]:
        (root / "train_package" / p).write_text("")

    (root / "preference_bank" / "preference_candidates.jsonl").write_text("")

    result = collect_dataset_scale(root)
    for key in (
        "existing_task_dirs", "sft_total", "preference_total",
        "preference_bank_total", "hard_preference_total", "training_readiness",
    ):
        assert key in result, f"missing key: {key}"


def test_collect_swe_bench_smoke_from_file(tmp_path: Path):
    smoke_file = tmp_path / "smoke.json"
    smoke_file.write_text(json.dumps({
        "total": 5, "resolved": 5, "unresolved": 0,
        "error_count": 0, "resolve_rate": 1.0,
        "all_gold_resolved": True, "all_empty_unresolved": True,
        "passed": True,
    }))
    result = collect_swe_bench_smoke(smoke_path=smoke_file)
    assert result["available"] is True
    assert result["passed"] is True
    assert result["total"] == 5


def test_collect_swe_bench_smoke_missing():
    result = collect_swe_bench_smoke(smoke_path=Path("/nonexistent/smoke.json"))
    assert result["available"] is False


# ---------------------------------------------------------------------------
# integration: build_report with mocks
# ---------------------------------------------------------------------------


def test_build_report_overall_pass_when_all_pass():
    """Integration test: mock all collectors to pass, verify report."""
    with patch("codeguide_agent.eval.harness_reporter.collect_git_info") as mg:
        mg.return_value = ("claude", "abc123")
        with patch("codeguide_agent.eval.harness_reporter.collect_dataset_scale") as ms:
            ms.return_value = {
                "existing_task_dirs": 100, "sft_total": 100,
                "preference_total": 169, "preference_bank_total": 169,
                "hard_preference_total": 64,
                "training_readiness": {"task_count_ge_100": True},
            }
            with patch("codeguide_agent.eval.harness_reporter.collect_p61_check") as mp:
                mp.return_value = {"passed": True}
                with patch("codeguide_agent.eval.harness_reporter.collect_wrapper_delegation") as mw:
                    mw.return_value = {"passed": True, "stdout": "OK: 6 wrappers"}
                    with patch("codeguide_agent.eval.harness_reporter.collect_swe_bench_smoke") as msw:
                        msw.return_value = {"available": True, "passed": True}
                        with patch("codeguide_agent.eval.harness_reporter.collect_test_suite") as mt:
                            mt.return_value = {"passed": True, "test_count": 198}
                            with patch("codeguide_agent.eval.harness_reporter.collect_audit") as ma:
                                ma.return_value = {"passed": True}
                                with patch("codeguide_agent.eval.harness_reporter.collect_clean_check") as mc:
                                    mc.return_value = {"passed": True}
                                    with patch("codeguide_agent.eval.harness_reporter.collect_compile_check") as mcc:
                                        mcc.return_value = {"passed": True}
                                        report = build_report()

    assert report.overall_status == "pass"
    assert report.branch == "claude"
    assert len(report.checks) == 8
    assert all(c.passed for c in report.checks)


def test_build_report_overall_fail_when_one_fails():
    with patch("codeguide_agent.eval.harness_reporter.collect_git_info") as mg:
        mg.return_value = ("claude", "abc123")
        with patch("codeguide_agent.eval.harness_reporter.collect_dataset_scale") as ms:
            ms.return_value = {"training_readiness": {"task_count_ge_100": True}}
            with patch("codeguide_agent.eval.harness_reporter.collect_p61_check") as mp:
                mp.return_value = {"passed": True}
                with patch("codeguide_agent.eval.harness_reporter.collect_wrapper_delegation") as mw:
                    mw.return_value = {"passed": False, "stdout": ""}
                    with patch("codeguide_agent.eval.harness_reporter.collect_swe_bench_smoke") as msw:
                        msw.return_value = {"available": False}
                        with patch("codeguide_agent.eval.harness_reporter.collect_test_suite") as mt:
                            mt.return_value = {"passed": True}
                            with patch("codeguide_agent.eval.harness_reporter.collect_audit") as ma:
                                ma.return_value = {"passed": True}
                                with patch("codeguide_agent.eval.harness_reporter.collect_clean_check") as mc:
                                    mc.return_value = {"passed": True}
                                    with patch("codeguide_agent.eval.harness_reporter.collect_compile_check") as mcc:
                                        mcc.return_value = {"passed": True}
                                        report = build_report()

    assert report.overall_status == "fail"


# ---------------------------------------------------------------------------
# CLI smoke: --help works, imports are clean
# ---------------------------------------------------------------------------


def test_cli_help():
    proc = subprocess.run(
        ["python", "scripts/run_eval_harness_report.py", "--help"],
        capture_output=True, text=True, timeout=30, cwd=str(Path(__file__).resolve().parents[1]),
        check=False,
    )
    assert proc.returncode == 0
    assert "--json" in proc.stdout
    assert "--markdown" in proc.stdout
