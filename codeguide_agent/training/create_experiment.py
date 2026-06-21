from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from codeguide_agent.training.data import load_training_package


DEFAULT_EXPERIMENTS_ROOT = Path("experiments/mini_repo_debug")
PACKAGE_FILES = (
    "sft_train.jsonl",
    "sft_eval.jsonl",
    "preference_train.jsonl",
    "preference_eval.jsonl",
    "manifest.json",
    "data_card.md",
)


def create_experiment(
    package: str | Path,
    mode: str,
    run_name: str,
    experiments_root: str | Path = DEFAULT_EXPERIMENTS_ROOT,
    batch_size: int = 4,
) -> dict[str, Any]:
    if mode not in {"sft", "preference"}:
        raise ValueError("mode must be 'sft' or 'preference'")
    run_dir = Path(experiments_root) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    package_path = Path(package)
    dataset = load_training_package(package_path, mode=mode, batch_size=batch_size)
    manifest = _read_json(package_path / "manifest.json")
    counts = {
        "train_records": len(dataset.train_records),
        "eval_records": len(dataset.eval_records),
        "batch_size": batch_size,
        "batch_count": dataset.batch_count,
    }
    config = {
        "run_name": run_name,
        "mode": mode,
        "package": str(package_path),
        "dataset_hash": _hash_package(package_path),
        "counts": counts,
        "package_counts": manifest.get("counts", {}),
        "git_commit": _git_commit(),
        "sanitization": {
            "passed": bool(dataset.quality_gate.get("passed")),
            "model_facing_records_checked": counts["train_records"] + counts["eval_records"],
            "forbidden_term_count": 4,
            "raw_output_fields_exported": False,
        },
        "training": {
            "real_training_run": False,
            "artifact_kind": "pending_mock_or_external",
        },
    }
    metrics = {
        "status": "created",
        "mode": mode,
        "train_records": counts["train_records"],
        "eval_records": counts["eval_records"],
        "quality_gate_passed": bool(dataset.quality_gate.get("passed")),
        "real_training_run": False,
    }
    artifacts = {
        "artifact_type": "none",
        "contains_model_weights": False,
        "patch_candidates": [],
        "notes": ["Experiment registered; no train artifact has been attached yet."],
    }
    replay_report = {
        "status": "not_run",
        "checked_records": 0,
        "patch_failures": [],
        "hidden_tests_run": False,
        "passed": None,
    }
    eval_summary = {
        "status": "not_run",
        "policy": "trained",
        "hidden_tests_run": False,
    }

    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "artifacts.json", artifacts)
    _write_json(run_dir / "replay_report.json", replay_report)
    _write_json(run_dir / "eval_summary.json", eval_summary)
    return {
        "run_dir": str(run_dir),
        "config_path": str(run_dir / "config.json"),
        "metrics_path": str(run_dir / "metrics.json"),
        "artifact_registry_path": str(run_dir / "artifacts.json"),
        "dataset_hash": config["dataset_hash"],
        "counts": counts,
        "sanitization": config["sanitization"],
    }


def _hash_package(package_path: Path) -> str:
    digest = hashlib.sha256()
    for name in PACKAGE_FILES:
        path = package_path / name
        if not path.exists():
            continue
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a CodeGuide Mini-Repo-Debug experiment registry entry.")
    parser.add_argument("--package", required=True, help="Path to a P6 train_package directory.")
    parser.add_argument("--mode", choices=["sft", "preference"], required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--experiments-root", default=str(DEFAULT_EXPERIMENTS_ROOT))
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    result = create_experiment(args.package, args.mode, args.run_name, args.experiments_root, args.batch_size)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
