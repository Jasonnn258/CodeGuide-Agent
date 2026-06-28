"""P1.5 eval harness reporter — collects local offline status checks into JSON + Markdown.

All operations are local. No external APIs, no training, no LLM calls.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class EvalHarnessReport:
    report_version: str = "1.0"
    generated_at: str = ""
    branch: str = ""
    commit: str = ""
    dataset_scale: dict[str, Any] = field(default_factory=dict)
    p61_check: dict[str, Any] = field(default_factory=dict)
    wrapper_delegation: dict[str, Any] = field(default_factory=dict)
    swe_bench_smoke: dict[str, Any] = field(default_factory=dict)
    test_suite: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    clean_check: dict[str, Any] = field(default_factory=dict)
    compile_check: dict[str, Any] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)
    overall_status: str = "unknown"


# ---------------------------------------------------------------------------
# collectors
# ---------------------------------------------------------------------------


def collect_git_info() -> tuple[str, str]:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = _git("rev-parse", "HEAD")
    return branch, commit


def collect_dataset_scale(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else REPO_ROOT / "data" / "mini_repo_debug"

    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    tasks = sorted((root / "tasks").glob("task_*") if (root / "tasks").exists() else [])
    repos = sorted((root / "repos").glob("task_*") if (root / "repos").exists() else [])
    backlog_path = root / "task_backlog.json"
    backlog = json.loads(backlog_path.read_text(encoding="utf-8")) if backlog_path.exists() else []

    package = root / "train_package"
    sft_total = len(_read_jsonl(package / "sft_train.jsonl")) + len(_read_jsonl(package / "sft_eval.jsonl"))
    pref_total = len(_read_jsonl(package / "preference_train.jsonl")) + len(_read_jsonl(package / "preference_eval.jsonl"))
    bank = _read_jsonl(root / "preference_bank" / "preference_candidates.jsonl")
    hard_pref = [
        r for r in bank
        if r.get("rejection_reason") == "public_pass_hidden_assertion_fail"
        or "hidden_assertion_fail" in r.get("reason_labels", [])
    ]

    existing = max(len(tasks), len(repos))
    return {
        "existing_task_dirs": existing,
        "planned_backlog_tasks": len(backlog),
        "target_total_tasks": existing + len(backlog),
        "sft_total": sft_total,
        "preference_total": pref_total,
        "preference_bank_total": len(bank),
        "hard_preference_total": len(hard_pref),
        "training_readiness": {
            "task_count_ge_100": existing + len(backlog) >= 100,
            "sft_total_ge_150": sft_total >= 150,
            "preference_total_ge_100": max(pref_total, len(bank)) >= 100,
            "hard_preference_total_ge_30": len(hard_pref) >= 30,
        },
    }


def collect_p61_check() -> dict[str, Any]:
    proc = _run([sys.executable, str(REPO_ROOT / "scripts" / "p61_check_rollout_exports.py")])
    return {
        "passed": proc["returncode"] == 0,
        "stdout_tail": _tail(proc["stdout"], 20),
        "stderr_tail": _tail(proc["stderr"], 10),
    }


def collect_wrapper_delegation() -> dict[str, Any]:
    proc = _run([sys.executable, str(REPO_ROOT / "scripts" / "test_wrapper_delegation.py")])
    return {
        "passed": proc["returncode"] == 0,
        "stdout": proc["stdout"].strip(),
        "stderr_tail": _tail(proc["stderr"], 10),
    }


def collect_swe_bench_smoke(smoke_path: Path | None = None) -> dict[str, Any]:
    if smoke_path is None:
        smoke_path = REPO_ROOT / "data" / "mini_repo_debug" / "swe_bench_smoke.json"
    if not smoke_path.exists():
        return {"available": False, "reason": "no smoke output file — run scripts/run_swe_bench_smoke.py"}
    try:
        data = json.loads(smoke_path.read_text(encoding="utf-8"))
        return {
            "available": True,
            "passed": data.get("passed", False),
            "total": data.get("total", 0),
            "resolved": data.get("resolved", 0),
            "resolve_rate": data.get("resolve_rate", 0.0),
            "all_gold_resolved": data.get("all_gold_resolved", False),
            "all_empty_unresolved": data.get("all_empty_unresolved", False),
        }
    except (json.JSONDecodeError, OSError) as exc:
        return {"available": False, "reason": f"failed to read smoke file: {exc}"}


def collect_test_suite() -> dict[str, Any]:
    proc = _run(["make", "test"], cwd=str(REPO_ROOT), timeout=180)
    test_count = _parse_pytest_count(proc["stdout"])
    return {
        "passed": proc["returncode"] == 0,
        "test_count": test_count,
        "stdout_tail": _tail(proc["stdout"], 5),
    }


def collect_audit() -> dict[str, Any]:
    proc = _run(["make", "audit"], cwd=str(REPO_ROOT))
    return {
        "passed": proc["returncode"] == 0,
        "stdout": proc["stdout"].strip(),
    }


def collect_clean_check() -> dict[str, Any]:
    proc = _run(["make", "clean-check"], cwd=str(REPO_ROOT))
    count = _parse_pytest_count(proc["stdout"])
    return {
        "passed": proc["returncode"] == 0,
        "test_count": count,
        "stdout_tail": _tail(proc["stdout"], 5),
    }


def collect_compile_check() -> dict[str, Any]:
    proc = _run(
        [sys.executable, "-m", "compileall", "codeguide_agent", "scripts"],
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    return {
        "passed": proc["returncode"] == 0,
        "stderr_tail": _tail(proc["stderr"], 10) if proc["returncode"] != 0 else "",
    }


# ---------------------------------------------------------------------------
# report builder
# ---------------------------------------------------------------------------


def build_report(root: Path | None = None) -> EvalHarnessReport:
    branch, commit = collect_git_info()
    generated_at = datetime.now(timezone.utc).isoformat()

    scale = collect_dataset_scale(root)
    p61 = collect_p61_check()
    wrapper = collect_wrapper_delegation()
    swe = collect_swe_bench_smoke()
    tests = collect_test_suite()
    audit = collect_audit()
    clean = collect_clean_check()
    compile_ = collect_compile_check()

    checks = [
        CheckResult(name="dataset_scale", passed=scale["training_readiness"]["task_count_ge_100"], details=scale),
        CheckResult(name="p61_check", passed=p61["passed"], details=p61),
        CheckResult(name="wrapper_delegation", passed=wrapper["passed"], details=wrapper),
        CheckResult(name="swe_bench_smoke", passed=swe.get("passed", False) if swe.get("available") else True, details=swe),
        CheckResult(name="test_suite", passed=tests["passed"], details=tests),
        CheckResult(name="audit", passed=audit["passed"], details=audit),
        CheckResult(name="clean_check", passed=clean["passed"], details=clean),
        CheckResult(name="compile_check", passed=compile_["passed"], details=compile_),
    ]

    all_passed = all(c.passed for c in checks if c.name != "swe_bench_smoke" or swe.get("available"))

    return EvalHarnessReport(
        generated_at=generated_at,
        branch=branch,
        commit=commit,
        dataset_scale=scale,
        p61_check=p61,
        wrapper_delegation=wrapper,
        swe_bench_smoke=swe,
        test_suite=tests,
        audit=audit,
        clean_check=clean,
        compile_check=compile_,
        checks=checks,
        overall_status="pass" if all_passed else "fail",
    )


# ---------------------------------------------------------------------------
# formatters
# ---------------------------------------------------------------------------


def format_json(report: EvalHarnessReport) -> str:
    data: dict[str, Any] = {
        "report_version": report.report_version,
        "generated_at": report.generated_at,
        "branch": report.branch,
        "commit": report.commit,
        "overall_status": report.overall_status,
        "dataset_scale": report.dataset_scale,
        "p61_check": _compact(report.p61_check),
        "wrapper_delegation": _compact(report.wrapper_delegation),
        "swe_bench_smoke": _compact(report.swe_bench_smoke),
        "test_suite": _compact(report.test_suite),
        "audit": _compact(report.audit),
        "clean_check": _compact(report.clean_check),
        "compile_check": _compact(report.compile_check),
        "checks": [asdict(c) for c in report.checks],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def format_markdown(report: EvalHarnessReport) -> str:
    lines: list[str] = []
    lines.append("# CodeGuide-Agent Eval Harness Report")
    lines.append("")
    lines.append(f"**Generated**: {report.generated_at}")
    lines.append(f"**Branch**: `{report.branch}`")
    lines.append(f"**Commit**: `{report.commit[:12]}`")
    lines.append(f"**Overall**: {'PASS' if report.overall_status == 'pass' else 'FAIL'}")
    lines.append("")

    lines.append("## Dataset Scale")
    lines.append("")
    s = report.dataset_scale
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    for k in ("existing_task_dirs", "planned_backlog_tasks", "target_total_tasks",
              "sft_total", "preference_total", "preference_bank_total", "hard_preference_total"):
        lines.append(f"| {k} | {s.get(k)} |")
    lines.append("")
    tr = s.get("training_readiness", {})
    lines.append("### Training Readiness")
    lines.append("")
    for k, v in tr.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")

    lines.append("## Checks")
    lines.append("")
    lines.append(f"| Check | Status | Detail |")
    lines.append(f"|-------|--------|--------|")
    for c in report.checks:
        status = "PASS" if c.passed else "FAIL"
        detail = _check_detail(c)
        lines.append(f"| {c.name} | {status} | {detail} |")
    lines.append("")

    lines.append("## SWE-bench Smoke")
    lines.append("")
    sw = report.swe_bench_smoke
    if sw.get("available"):
        lines.append(f"- total: {sw.get('total')}")
        lines.append(f"- resolved: {sw.get('resolved')}")
        lines.append(f"- resolve_rate: {sw.get('resolve_rate')}")
        lines.append(f"- all_gold_resolved: {sw.get('all_gold_resolved')}")
        lines.append(f"- all_empty_unresolved: {sw.get('all_empty_unresolved')}")
    else:
        lines.append(f"- unavailable: {sw.get('reason', 'no data')}")
    lines.append("")

    lines.append("## Raw Output")
    lines.append("")
    lines.append("### Wrapper Delegation")
    lines.append("```")
    lines.append(report.wrapper_delegation.get("stdout", ""))
    lines.append("```")
    lines.append("")
    lines.append("### Audit")
    lines.append("```")
    lines.append(report.audit.get("stdout", ""))
    lines.append("```")
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _git(*args: str) -> str:
    proc = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT), check=False)
    return proc.stdout.strip()


def _run(command: list[str], cwd: str = "", timeout: int = 90) -> dict[str, Any]:
    cwd = cwd or str(REPO_ROOT)
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=cwd, check=False)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _tail(text: str, n: int) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-n:]) if len(lines) > n else text.strip()


def _parse_pytest_count(text: str) -> int:
    import re
    m = re.search(r"(\d+)\s+passed", text)
    return int(m.group(1)) if m else 0


def _compact(d: dict[str, Any]) -> dict[str, Any]:
    """Return a compact dict suitable for JSON, dropping verbose stdout/stderr tails when passed."""
    result = dict(d)
    if result.get("passed"):
        result.pop("stdout_tail", None)
        result.pop("stderr_tail", None)
        result.pop("stdout", None)
        result.pop("stderr", None)
    return result


def _check_detail(c: CheckResult) -> str:
    if c.name == "dataset_scale":
        s = c.details
        return f"{s.get('existing_task_dirs')} tasks, {s.get('sft_total')} SFT, {s.get('preference_total')} pref, {s.get('hard_preference_total')} hard"
    if c.name == "test_suite" or c.name == "clean_check":
        return f"{c.details.get('test_count', '?')} passed"
    if c.name == "wrapper_delegation":
        return c.details.get("stdout", "?").replace("OK: ", "").strip()
    if c.name == "swe_bench_smoke":
        if not c.details.get("available"):
            return "no smoke data"
        return f"{c.details.get('resolved')}/{c.details.get('total')} resolved"
    return "passed" if c.passed else "failed"
