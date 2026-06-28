"""P1.7 Consolidated Offline Eval/Ablation Report.

Sources: docs/ROADMAP_CONTEXT_RAG_TRAINING.md P1.7 — consolidate the outputs of
the P1.5 eval harness, the P1.6 dataset quality diagnostics, and the three
RAG offline ablation scripts (history RAG ablation, code RAG localization,
agent loop ablation) into a single local offline report.

The report is JSON + Markdown. It performs no training, no external API calls,
no LLM calls, and surfaces no gold/hidden/oracle content — only summary
metadata from each underlying artifact. RAG sections are optional: missing
output files degrade to ``available=False`` and do not fail the overall
report; present-but-failed RAG outputs do fail the overall report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codeguide_agent.eval.harness_reporter import (
    EvalHarnessReport,
    build_report as _harness_build_report,
)
from codeguide_agent.eval.dataset_quality import (
    DatasetQualityReport,
    build_quality_report as _quality_build,
)

REPORT_VERSION = "1.0"


@dataclass
class SectionResult:
    name: str
    available: bool
    passed: bool
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsolidatedOfflineReport:
    report_version: str = REPORT_VERSION
    generated_at: str = ""
    branch: str = ""
    commit: str = ""
    overall_status: str = "unknown"
    eval_harness: dict[str, Any] = field(default_factory=dict)
    dataset_quality: dict[str, Any] = field(default_factory=dict)
    p61_check: dict[str, Any] = field(default_factory=dict)
    wrapper_delegation: dict[str, Any] = field(default_factory=dict)
    swe_bench_smoke: dict[str, Any] = field(default_factory=dict)
    history_rag_ablation: dict[str, Any] = field(default_factory=dict)
    code_rag_localization: dict[str, Any] = field(default_factory=dict)
    agent_loop_ablation: dict[str, Any] = field(default_factory=dict)
    sections: list[SectionResult] = field(default_factory=list)


def _build_harness_report(root: Path) -> EvalHarnessReport:
    return _harness_build_report(root)


def _build_quality_report(root: Path) -> DatasetQualityReport:
    return _quality_build(root)


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_history_rag_ablation(root: Path) -> dict[str, Any]:
    """Read ``history_index/ablation_results.json`` if present."""
    path = root / "history_index" / "ablation_results.json"
    if not path.exists():
        return {"available": False, "reason": f"missing {path.name}"}
    try:
        data = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return {"available": False, "reason": "corrupt or unreadable JSON"}

    modes = data.get("modes", {}) if isinstance(data, dict) else {}
    quality = modes.get("quality", {}) if isinstance(modes, dict) else {}
    leakage = data.get("leakage", {}) if isinstance(data, dict) else {}
    return {
        "available": True,
        "overall_passed": bool(data.get("overall_passed", False)),
        "total_records": int(data.get("total_records", 0)),
        "unique_tasks": int(data.get("unique_tasks", 0)),
        "unique_families": int(data.get("unique_families", 0)),
        "leakage_passed": bool(leakage.get("passed", False)) if isinstance(leakage, dict) else False,
        "quality_mode": {
            "passed": bool(quality.get("passed", False)),
            "family_hit_at_1": quality.get("family_hit_at_1"),
            "family_hit_at_3": quality.get("family_hit_at_3"),
            "family_hit_at_5": quality.get("family_hit_at_5"),
            "total_queries": quality.get("total_queries"),
            "coverage_empty_pct": quality.get("coverage_empty_pct"),
            "leakage_safe": bool(quality.get("leakage_safe", False)),
        },
    }


def collect_code_rag_localization(root: Path) -> dict[str, Any]:
    """Read ``code_index/localization_eval.json`` if present."""
    path = root / "code_index" / "localization_eval.json"
    if not path.exists():
        return {"available": False, "reason": f"missing {path.name}"}
    try:
        data = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return {"available": False, "reason": "corrupt or unreadable JSON"}

    return {
        "available": True,
        "passed": bool(data.get("passed", False)),
        "num_tasks": int(data.get("num_tasks", 0)),
        "valid_tasks": int(data.get("valid_tasks", 0)),
        "avg_chunks_per_task": data.get("avg_chunks_per_task"),
        "file_hit_at_1": data.get("file_hit_at_1"),
        "file_hit_at_3": data.get("file_hit_at_3"),
        "file_hit_at_5": data.get("file_hit_at_5"),
        "symbol_hit_at_1": data.get("symbol_hit_at_1"),
        "symbol_hit_at_3": data.get("symbol_hit_at_3"),
        "symbol_hit_at_5": data.get("symbol_hit_at_5"),
    }


def collect_agent_loop_ablation(root: Path) -> dict[str, Any]:
    """Read ``history_index/agent_loop_ablation.json`` if present."""
    path = root / "history_index" / "agent_loop_ablation.json"
    if not path.exists():
        return {"available": False, "reason": f"missing {path.name}"}
    try:
        data = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return {"available": False, "reason": "corrupt or unreadable JSON"}

    disabled = data.get("disabled", {}) if isinstance(data, dict) else {}
    enabled = data.get("enabled", {}) if isinstance(data, dict) else {}
    return {
        "available": True,
        "overall_passed": bool(data.get("overall_passed", False)),
        "disabled": {
            "total_tasks": int(disabled.get("total_tasks", 0)),
            "total_snippets": int(disabled.get("total_snippets", 0)),
            "leakage_safe": bool(disabled.get("leakage_safe", False)),
        },
        "enabled": {
            "total_tasks": int(enabled.get("total_tasks", 0)),
            "total_snippets": int(enabled.get("total_snippets", 0)),
            "avg_snippets_per_task": enabled.get("avg_snippets_per_task"),
            "same_family_warnings": int(enabled.get("same_family_warnings", 0)),
            "leakage_safe": bool(enabled.get("leakage_safe", False)),
        },
    }


def _git(*args: str) -> str:
    import subprocess
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except Exception:
        return ""


def build_consolidated_report(root: Path | None = None) -> ConsolidatedOfflineReport:
    root = Path(root) if root is not None else Path("data/mini_repo_debug")

    harness = _build_harness_report(root)
    quality = _build_quality_report(root)
    hist = collect_history_rag_ablation(root)
    code = collect_code_rag_localization(root)
    agent = collect_agent_loop_ablation(root)

    harness_status = harness.overall_status == "pass"
    quality_status = quality.overall_status == "pass"

    optional_statuses: list[bool] = []
    if hist.get("available"):
        optional_statuses.append(bool(hist.get("overall_passed", False)))
    if code.get("available"):
        optional_statuses.append(bool(code.get("passed", False)))
    if agent.get("available"):
        optional_statuses.append(bool(agent.get("overall_passed", False)))

    overall_pass = harness_status and quality_status and all(optional_statuses)

    report = ConsolidatedOfflineReport(
        report_version=REPORT_VERSION,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
        commit=_git("rev-parse", "--short", "HEAD"),
        overall_status="pass" if overall_pass else "fail",
        eval_harness=_harness_to_dict(harness),
        dataset_quality=_quality_to_dict(quality),
        p61_check=_compact_pass_dict(harness.p61_check),
        wrapper_delegation=_compact_pass_dict(harness.wrapper_delegation),
        swe_bench_smoke=_compact_pass_dict(harness.swe_bench_smoke),
        history_rag_ablation=hist,
        code_rag_localization=code,
        agent_loop_ablation=agent,
    )

    report.sections = _build_sections(report, harness, quality, hist, code, agent)
    return report


def _harness_to_dict(report: EvalHarnessReport) -> dict[str, Any]:
    return {
        "report_version": report.report_version,
        "generated_at": report.generated_at,
        "branch": report.branch,
        "commit": report.commit,
        "overall_status": report.overall_status,
        "dataset_scale": report.dataset_scale,
        "test_suite": report.test_suite,
        "audit": report.audit,
        "clean_check": report.clean_check,
        "compile_check": report.compile_check,
    }


def _quality_to_dict(report: DatasetQualityReport) -> dict[str, Any]:
    return {
        "report_version": report.report_version,
        "total_tasks": report.total_tasks,
        "overall_status": report.overall_status,
        "by_source": report.by_source,
        "by_split": report.by_split,
        "by_difficulty": report.by_difficulty,
        "by_bug_type": report.by_bug_type,
        "by_generator_family": report.by_generator_family,
        "flags": report.flags,
    }


def _compact_pass_dict(d: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    out = dict(d)
    for k in ("stdout", "stderr"):
        if k in out and out.get("passed") is True:
            out.pop(k, None)
    return out


def _build_sections(
    report: ConsolidatedOfflineReport,
    harness: EvalHarnessReport,
    quality: DatasetQualityReport,
    hist: dict[str, Any],
    code: dict[str, Any],
    agent: dict[str, Any],
) -> list[SectionResult]:
    s: list[SectionResult] = []

    s.append(SectionResult(
        name="eval_harness",
        available=True,
        passed=harness.overall_status == "pass",
        summary=f"overall_status={harness.overall_status}",
        details={},
    ))
    s.append(SectionResult(
        name="dataset_quality",
        available=True,
        passed=quality.overall_status == "pass",
        summary=f"total_tasks={quality.total_tasks}, overall_status={quality.overall_status}",
        details={},
    ))
    s.append(SectionResult(
        name="p61_check",
        available=True,
        passed=bool(report.p61_check.get("passed", False)),
        summary=str(report.p61_check.get("stdout", ""))[:80] or "p61-check",
        details=report.p61_check,
    ))
    s.append(SectionResult(
        name="wrapper_delegation",
        available=True,
        passed=bool(report.wrapper_delegation.get("passed", False)),
        summary=str(report.wrapper_delegation.get("stdout", ""))[:80] or "wrapper delegation",
        details=report.wrapper_delegation,
    ))
    s.append(SectionResult(
        name="swe_bench_smoke",
        available=bool(report.swe_bench_smoke.get("available", False)),
        passed=bool(report.swe_bench_smoke.get("passed", False)) if report.swe_bench_smoke.get("available") else True,
        summary=str(report.swe_bench_smoke.get("reason", ""))[:80] or "swe-bench smoke",
        details=report.swe_bench_smoke,
    ))
    s.append(SectionResult(
        name="history_rag_ablation",
        available=bool(hist.get("available", False)),
        passed=bool(hist.get("overall_passed", False)) if hist.get("available") else True,
        summary=(f"records={hist.get('total_records', 0)}, passed={hist.get('overall_passed')}" if hist.get("available") else "absent"),
        details=hist,
    ))
    s.append(SectionResult(
        name="code_rag_localization",
        available=bool(code.get("available", False)),
        passed=bool(code.get("passed", False)) if code.get("available") else True,
        summary=(f"symbol_hit@1={code.get('symbol_hit_at_1')}, passed={code.get('passed')}" if code.get("available") else "absent"),
        details=code,
    ))
    s.append(SectionResult(
        name="agent_loop_ablation",
        available=bool(agent.get("available", False)),
        passed=bool(agent.get("overall_passed", False)) if agent.get("available") else True,
        summary=(f"snippets(enabled)={agent.get('enabled', {}).get('total_snippets')}, passed={agent.get('overall_passed')}" if agent.get("available") else "absent"),
        details=agent,
    ))
    return s


def format_json(report: ConsolidatedOfflineReport) -> str:
    payload = {
        "report_version": report.report_version,
        "generated_at": report.generated_at,
        "branch": report.branch,
        "commit": report.commit,
        "overall_status": report.overall_status,
        "eval_harness": report.eval_harness,
        "dataset_quality": report.dataset_quality,
        "p61_check": report.p61_check,
        "wrapper_delegation": report.wrapper_delegation,
        "swe_bench_smoke": report.swe_bench_smoke,
        "history_rag_ablation": report.history_rag_ablation,
        "code_rag_localization": report.code_rag_localization,
        "agent_loop_ablation": report.agent_loop_ablation,
        "sections": [asdict(s) for s in report.sections],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def format_markdown(report: ConsolidatedOfflineReport) -> str:
    status_label = "PASS" if report.overall_status == "pass" else "FAIL"
    lines: list[str] = []
    lines.append("# CodeGuide-Agent Consolidated Offline Report")
    lines.append("")
    lines.append(f"- generated_at: `{report.generated_at}`")
    lines.append(f"- branch: `{report.branch}`")
    lines.append(f"- commit: `{report.commit}`")
    lines.append(f"- report_version: `{report.report_version}`")
    lines.append(f"- overall_status: **{status_label}** (`{report.overall_status}`)")
    lines.append("")
    lines.append("## Sections")
    lines.append("")
    lines.append("| section | available | passed | summary |")
    lines.append("| --- | --- | --- | --- |")
    for s in report.sections:
        lines.append(
            f"| {s.name} | {s.available} | {s.passed} | {s.summary} |"
        )
    lines.append("")
    for name, payload in (
        ("eval_harness", report.eval_harness),
        ("dataset_quality", report.dataset_quality),
        ("p61_check", report.p61_check),
        ("wrapper_delegation", report.wrapper_delegation),
        ("swe_bench_smoke", report.swe_bench_smoke),
        ("history_rag_ablation", report.history_rag_ablation),
        ("code_rag_localization", report.code_rag_localization),
        ("agent_loop_ablation", report.agent_loop_ablation),
    ):
        lines.append(f"## {name}")
        lines.append("```json")
        lines.append(json.dumps(payload, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)
