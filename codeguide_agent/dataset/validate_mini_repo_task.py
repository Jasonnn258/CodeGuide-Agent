from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.schemas import REQUIRED_METADATA_FIELDS, MiniRepoTask, load_metadata
from codeguide_agent.tools.run_test import run_test


REQUIRED_PATHS = ["metadata.json", "issue.md", "tests", "tests_hidden", "gold.patch"]


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)


def validate_task(task_dir: str | Path) -> dict[str, Any]:
    task_path = Path(task_dir)
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_PATHS:
        path = task_path / relative
        if not path.exists():
            errors.append(f"missing required path: {relative}")

    metadata: dict[str, Any] = {}
    if (task_path / "metadata.json").exists():
        try:
            metadata = load_metadata(task_path)
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is invalid JSON: {exc}")
    else:
        metadata = {}

    missing_fields = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    for field in missing_fields:
        errors.append(f"missing metadata field: {field}")

    if metadata:
        for command_field in ("public_test_cmd", "hidden_test_cmd"):
            if not isinstance(metadata.get(command_field), str) or not metadata.get(command_field, "").strip():
                errors.append(f"{command_field} must be a non-empty string")

        if not _is_non_empty_list(metadata.get("gold_files")):
            errors.append("gold_files must be a non-empty list of strings")
        if not _is_non_empty_list(metadata.get("gold_functions")):
            errors.append("gold_functions must be a non-empty list of strings")
        if not _is_non_empty_list(metadata.get("forbidden_behaviors")):
            errors.append("forbidden_behaviors must be a non-empty list of strings")

        repo_path_value = metadata.get("repo_path")
        if not isinstance(repo_path_value, str) or not repo_path_value:
            errors.append("repo_path must be a non-empty string")
        else:
            repo_path = Path(repo_path_value)
            if not repo_path.is_absolute():
                repo_path = Path.cwd() / repo_path
            try:
                if repo_path.resolve() != task_path.resolve():
                    errors.append(f"repo_path does not match task directory: {repo_path_value}")
            except FileNotFoundError:
                errors.append(f"repo_path is not valid: {repo_path_value}")

        try:
            MiniRepoTask.from_metadata(metadata)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))

        if not errors and metadata.get("public_test_cmd"):
            public_result = run_test(task_path, metadata["public_test_cmd"], timeout=30)
            if _public_pass_count(public_result) == 0:
                warnings.append("public test suite has zero passing tests in the pre-patch state; regression detection will be weak")

    return {"task_dir": str(task_path), "valid": not errors, "errors": errors, "warnings": warnings}


def iter_task_dirs(root: str | Path) -> list[Path]:
    root_path = Path(root)
    repos = root_path / "repos"
    if repos.exists():
        return sorted(path for path in repos.iterdir() if path.is_dir())
    return sorted(path for path in root_path.iterdir() if path.is_dir() and path.name.startswith("task_"))


def validate_root(root: str | Path) -> dict[str, Any]:
    results = [validate_task(task_dir) for task_dir in iter_task_dirs(root)]
    return {
        "root": str(root),
        "valid": all(result["valid"] for result in results) and bool(results),
        "num_tasks": len(results),
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Mini-Repo-Debug task directories.")
    parser.add_argument("--root", default="data/mini_repo_debug", help="Dataset root containing repos/")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    result = validate_root(args.root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Validated {result['num_tasks']} task(s) under {args.root}")
        for task in result["tasks"]:
            status = "PASS" if task["valid"] else "FAIL"
            print(f"{status} {task['task_dir']}")
            for error in task["errors"]:
                print(f"  - {error}")
            for warning in task.get("warnings", []):
                print(f"  warning: {warning}")
    return 0 if result["valid"] else 1


def _public_pass_count(result: dict[str, Any]) -> int:
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    matches = re.findall(r"(\d+)\s+passed", text)
    if matches:
        return sum(int(value) for value in matches)
    return 1 if result.get("exit_code") == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
