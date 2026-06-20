from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.dataset.validate_mini_repo_task import iter_task_dirs


def audit_task(task_dir: str | Path) -> dict[str, Any]:
    task_path = Path(task_dir)
    metadata = load_metadata(task_path)
    issue_path = task_path / metadata.get("issue_path", "issue.md")
    issue_text = issue_path.read_text(encoding="utf-8") if issue_path.exists() else ""
    leaked_gold_files = sorted({item for item in metadata.get("gold_files", []) if item and item in issue_text})
    leaked_gold_functions = sorted({item for item in metadata.get("gold_functions", []) if item and item in issue_text})
    forbidden_mentions = sorted(
        token
        for token in ("metadata.json", "gold.patch", "tests_hidden")
        if token in issue_text
    )
    leakage = bool(leaked_gold_files or leaked_gold_functions or forbidden_mentions)
    return {
        "task_id": metadata.get("task_id", task_path.name),
        "task_dir": str(task_path),
        "leakage_detected": leakage,
        "leaked_gold_files": leaked_gold_files,
        "leaked_gold_functions": leaked_gold_functions,
        "forbidden_mentions": forbidden_mentions,
    }


def audit_root(root: str | Path) -> dict[str, Any]:
    results = [audit_task(task_dir) for task_dir in iter_task_dirs(root)]
    return {
        "root": str(root),
        "num_tasks": len(results),
        "leakage_detected": any(result["leakage_detected"] for result in results),
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Mini-Repo-Debug issue text for evaluator-only leakage.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit_root(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Leakage audit: {report['num_tasks']} task(s) under {args.root}")
        for task in report["tasks"]:
            status = "FAIL" if task["leakage_detected"] else "PASS"
            print(f"{status} {task['task_id']}")
            if task["leaked_gold_files"]:
                print(f"  leaked_gold_files: {task['leaked_gold_files']}")
            if task["leaked_gold_functions"]:
                print(f"  leaked_gold_functions: {task['leaked_gold_functions']}")
            if task["forbidden_mentions"]:
                print(f"  forbidden_mentions: {task['forbidden_mentions']}")
    return 1 if report["leakage_detected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
