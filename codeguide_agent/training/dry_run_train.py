from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.training.data import format_preference_record, format_sft_record, load_training_package


def run_dry_train(
    package: str | Path,
    mode: str,
    out_dir: str | Path | None = None,
    batch_size: int = 4,
) -> dict[str, Any]:
    dataset = load_training_package(package, mode=mode, batch_size=batch_size)
    run_dir = Path(out_dir) if out_dir is not None else Path(package) / "dry_runs" / mode
    run_dir.mkdir(parents=True, exist_ok=True)

    if mode == "sft":
        formatted_preview = [format_sft_record(record) for record in dataset.preview_batch]
    elif mode == "preference":
        formatted_preview = [format_preference_record(record) for record in dataset.preview_batch]
    else:
        raise ValueError("mode must be 'sft' or 'preference'")

    preview_path = run_dir / "formatted_preview.json"
    preview_path.write_text(json.dumps(formatted_preview, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "mode": mode,
        "dry_run": True,
        "package": str(Path(package)),
        "run_dir": str(run_dir),
        "train_records": len(dataset.train_records),
        "eval_records": len(dataset.eval_records),
        "batch_size": batch_size,
        "batch_count": dataset.batch_count,
        "quality_gate_passed": dataset.quality_gate.get("passed", False),
        "formatted_preview_path": str(preview_path),
        "notes": [
            "No model was downloaded.",
            "No GPU was required.",
            "No paid API was called.",
        ],
    }
    summary_path = run_dir / "dry_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {**summary, "summary_path": str(summary_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run CodeGuide training data loading and batching.")
    parser.add_argument("--package", required=True, help="Path to P6 train_package")
    parser.add_argument("--mode", choices=["sft", "preference"], required=True)
    parser.add_argument("--out-dir")
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    result = run_dry_train(args.package, args.mode, args.out_dir, args.batch_size)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
