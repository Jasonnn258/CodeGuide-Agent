from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.prepare_training_package import validate_training_package
from codeguide_agent.reward.hacking_checks import changed_files_from_diff


def replay_run(run_dir: str | Path, root: str | Path = "data/mini_repo_debug") -> dict[str, Any]:
    run_path = Path(run_dir)
    summary_path = run_path / "dry_run_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"missing dry_run_summary.json in {run_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    package_path = Path(summary["package"])
    quality_gate = validate_training_package(root, package_path)
    records = _load_mode_records(package_path, summary["mode"])

    checked = 0
    failures: list[dict[str, Any]] = []
    for record in records:
        for task_id, patch in _patches_for_record(record):
            checked += 1
            changed_files = changed_files_from_diff(patch)
            task_path = Path(root) / "repos" / task_id
            missing = [file_name for file_name in changed_files if not (task_path / file_name).exists()]
            if not patch.startswith("diff --git") or missing:
                failures.append({"task_id": task_id, "missing_files": missing, "has_diff": patch.startswith("diff --git")})

    result = {
        "run_dir": str(run_path),
        "mode": summary["mode"],
        "package": str(package_path),
        "checked_records": checked,
        "patch_failures": failures,
        "quality_gate_passed": quality_gate.get("passed", False),
        "hidden_tests_run": False,
        "passed": quality_gate.get("passed", False) and not failures,
    }
    report_path = run_path / "replay_report.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return {**result, "report_path": str(report_path)}


def _load_mode_records(package_path: Path, mode: str) -> list[dict[str, Any]]:
    if mode == "sft":
        names = ["sft_train.jsonl", "sft_eval.jsonl"]
    elif mode == "preference":
        names = ["preference_train.jsonl", "preference_eval.jsonl"]
    else:
        raise ValueError("run summary has invalid mode")
    records: list[dict[str, Any]] = []
    for name in names:
        path = package_path / name
        records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return records


def _patches_for_record(record: dict[str, Any]) -> list[tuple[str, str]]:
    task_id = str(record.get("task_id", ""))
    if record.get("record_type") == "codeguide_sft_v1":
        return [(task_id, str(record.get("final_patch", "")))]
    if record.get("record_type") == "codeguide_preference_v1":
        return [
            (task_id, str(record.get("chosen", {}).get("final_patch", ""))),
            (task_id, str(record.get("rejected", {}).get("final_patch", ""))),
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay-inspect a CodeGuide dry-run training directory.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--root", default="data/mini_repo_debug")
    args = parser.parse_args()

    result = replay_run(args.run_dir, args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
