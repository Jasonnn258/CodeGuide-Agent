#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "issue.md",
    "metadata.json",
    "src/placeholder.py",
    "tests/test_public_placeholder.py",
    "tests_hidden/test_hidden_placeholder.py",
    "gold.patch",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check_task(task_dir: Path) -> dict[str, Any]:
    task_id = task_dir.name
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (task_dir / rel).exists():
            errors.append(f"missing required file: {rel}")

    issue = read_text(task_dir / "issue.md")
    metadata = load_json(task_dir / "metadata.json")
    public_test = read_text(task_dir / "tests/test_public_placeholder.py")
    hidden_test = read_text(task_dir / "tests_hidden/test_hidden_placeholder.py")
    source = read_text(task_dir / "src/placeholder.py")
    gold = read_text(task_dir / "gold.patch")

    if "TODO" in issue:
        errors.append("issue.md still contains TODO")
    if "TODO" in public_test:
        errors.append("public test still contains TODO")
    if "TODO" in hidden_test:
        errors.append("hidden test still contains TODO")
    if "TODO" in source:
        errors.append("source file still contains TODO")
    if "TODO" in gold:
        errors.append("gold.patch still contains TODO")

    if "placeholder" in public_test:
        errors.append("public test still uses placeholder test")
    if "placeholder" in hidden_test:
        errors.append("hidden test still uses placeholder test")
    if "placeholder" in source:
        errors.append("source implementation still uses placeholder")

    if not gold.startswith("diff --git"):
        errors.append("gold.patch is not a real unified git diff")

    if metadata.get("status") == "planned_skeleton":
        errors.append("metadata status is still planned_skeleton")

    if metadata.get("task_id") != task_id:
        errors.append("metadata task_id does not match directory name")

    if not metadata.get("target_files"):
        errors.append("metadata target_files is empty")
    if not metadata.get("target_functions"):
        warnings.append("metadata target_functions is empty")

    if metadata.get("expected_failure_mode") in {None, "", "to_be_defined"}:
        errors.append("expected_failure_mode is not defined")

    if metadata.get("generalization_axis") in {None, "", "to_be_defined"}:
        errors.append("generalization_axis is not defined")

    forbidden_issue_terms = ["tests_hidden", "metadata.json", "gold.patch", "apply_gold_patch"]
    for term in forbidden_issue_terms:
        if term in issue:
            errors.append(f"issue.md leaks forbidden term: {term}")

    ready = not errors

    return {
        "task_id": task_id,
        "ready": ready,
        "errors": errors,
        "warnings": warnings,
        "task_dir": str(task_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planned-root", default="data/mini_repo_debug/planned_task_skeletons")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--report", default="docs/TASK_PROMOTION_READINESS_REPORT.json")
    args = parser.parse_args()

    planned_root = Path(args.planned_root)

    if args.task_id:
        task_dirs = [planned_root / args.task_id]
    else:
        task_dirs = sorted(p for p in planned_root.glob("task_*") if p.is_dir())

    if not task_dirs:
        raise SystemExit(f"no planned task directories found under {planned_root}")

    results = [check_task(task_dir) for task_dir in task_dirs]
    ready = [r for r in results if r["ready"]]
    blocked = [r for r in results if not r["ready"]]

    report = {
        "planned_root": str(planned_root),
        "checked": len(results),
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "results": results,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# Task Promotion Readiness Report")
    print(f"- planned_root: {planned_root}")
    print(f"- checked: {len(results)}")
    print(f"- ready_count: {len(ready)}")
    print(f"- blocked_count: {len(blocked)}")
    print(f"- report: {report_path}")

    if args.task_id:
        result = results[0]
        print()
        print(f"## {result['task_id']}")
        print(f"- ready: {result['ready']}")
        if result["errors"]:
            print("- errors:")
            for error in result["errors"]:
                print(f"  - {error}")
        if result["warnings"]:
            print("- warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        if not result["ready"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
