from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.training.data import load_training_package


def create_mock_artifact(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    config_path = run_path / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"missing config.json in {run_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    mode = str(config["mode"])
    package_path = Path(config["package"])
    dataset = load_training_package(package_path, mode=mode)
    patch_candidates = _patch_candidates(dataset.train_records + dataset.eval_records, mode)

    metadata = {
        "artifact_type": "mock_adapter",
        "contains_model_weights": False,
        "mode": mode,
        "dataset_hash": config.get("dataset_hash", ""),
        "candidate_count": len(patch_candidates),
        "notes": [
            "Deterministic metadata-only artifact.",
            "Real SFT/DPO adapters can replace this file later.",
        ],
    }
    artifact_path = run_path / "mock_adapter_info.json"
    artifact_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    artifacts = {
        **metadata,
        "artifact_path": str(artifact_path),
        "patch_candidates": patch_candidates,
    }
    (run_path / "artifacts.json").write_text(json.dumps(artifacts, indent=2, sort_keys=True), encoding="utf-8")
    metrics = _read_json(run_path / "metrics.json")
    metrics.update(
        {
            "status": "mock_artifact_created",
            "artifact_type": "mock_adapter",
            "contains_model_weights": False,
            "patch_candidate_count": len(patch_candidates),
        }
    )
    (run_path / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return artifacts


def _patch_candidates(records: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item.get("task_id", ""))):
        task_id = str(record.get("task_id", ""))
        if mode == "sft":
            patch = str(record.get("final_patch", ""))
            source = "sft_success"
        else:
            patch = str(record.get("chosen", {}).get("final_patch", ""))
            source = "preference_chosen"
        if patch.startswith("diff --git"):
            candidates.append({"task_id": task_id, "source": source, "final_patch": patch})
    return candidates


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach a deterministic mock train artifact to a CodeGuide experiment.")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    result = create_mock_artifact(args.run_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
