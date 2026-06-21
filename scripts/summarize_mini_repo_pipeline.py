from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def bullet_scalar(lines: list[str], data: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        if key in data:
            lines.append(f"- {key}: `{data[key]}`")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--experiment", default="experiments/mini_repo_debug/p10_pipeline_smoke")
    parser.add_argument("--out", default="docs/snapshots/mini_repo_debug_p4_p10_summary.md")
    args = parser.parse_args()

    root = Path(args.root)
    exp = Path(args.experiment)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Mini-Repo-Debug P4-P10 Summary")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- P4: expanded Mini-Repo-Debug to 20 tasks.")
    lines.append("- P5: exported SFT/preference candidates.")
    lines.append("- P6: built train-ready package with quality gate.")
    lines.append("- P7: added dry-run training scaffold.")
    lines.append("- P8: added experiment loop scaffold.")
    lines.append("- P9: expanded preference candidates.")
    lines.append("- P10: added one-command offline validation and project snapshot.")
    lines.append("- No real model training, GRPO, or paid API call is required for this snapshot.")
    lines.append("")

    task_count = count_jsonl(root / "tasks.jsonl")
    lines.append("## Dataset")
    lines.append("")
    lines.append(f"- task_count: `{task_count}`")
    lines.append("")

    eval_data = load_json(root / "reports" / "eval_compare.json")
    llm = (eval_data.get("summary") or eval_data.get("policy_summary") or {}).get("llm", {})
    if llm:
        lines.append("## Real LLM Baseline")
        lines.append("")
        bullet_scalar(lines, llm, [
            "num_tasks",
            "success_rate",
            "public_pass_rate",
            "hidden_pass_rate",
            "public_pass_hidden_fail_rate",
            "leakage_rate",
            "syntax_error_rate",
            "original_repo_unchanged_rate",
            "invalid_action_rate",
            "average_llm_calls",
            "hidden_failure_type_counts",
            "patch_generalization_risk_counts",
        ])
        lines.append("")

    export_summary = load_json(root / "exports" / "p5_export_summary.json")
    lines.append("## P5 Exports")
    lines.append("")
    lines.append(f"- sft_records: `{count_jsonl(root / 'exports' / 'p5_sft_rollouts.jsonl')}`")
    lines.append(f"- preference_pairs: `{count_jsonl(root / 'exports' / 'p5_preference_pairs.jsonl')}`")
    bullet_scalar(lines, export_summary, [
        "sft_record_count",
        "preference_pair_count",
        "task_009_preference_pair_generated",
    ])
    lines.append("")

    pref_summary = load_json(root / "preference_bank" / "preference_bank_summary.json")
    lines.append("## P9 Preference Bank")
    lines.append("")
    lines.append(f"- preference_candidates: `{count_jsonl(root / 'preference_bank' / 'preference_candidates.jsonl')}`")
    bullet_scalar(lines, pref_summary, [
        "input_candidates",
        "duplicates_removed",
        "output_candidates",
        "task_coverage",
        "source_counts",
        "rejection_reason_counts",
    ])
    lines.append("")

    manifest = load_json(root / "train_package" / "manifest.json")
    lines.append("## P6/P9 Train Package")
    lines.append("")
    bullet_scalar(lines, manifest, [
        "sft_train_count",
        "sft_eval_count",
        "sft_total_count",
        "preference_train_count",
        "preference_eval_count",
        "preference_total_count",
        "quality_gate_passed",
    ])
    if manifest.get("warnings"):
        lines.append(f"- warnings: `{manifest['warnings']}`")
    lines.append("")

    eval_summary = load_json(exp / "eval_summary.json")
    replay_report = load_json(exp / "replay_report.json")
    lines.append("## P8/P10 Experiment Smoke")
    lines.append("")
    lines.append(f"- experiment_dir: `{exp}`")
    bullet_scalar(lines, eval_summary, [
        "checked_tasks",
        "predicted_tasks",
        "patch_inspection_pass_rate",
        "leakage_rate",
        "verifier_only_tests_run",
    ])
    bullet_scalar(lines, replay_report, [
        "checked_records",
        "quality_gate_passed",
        "passed",
        "hidden_tests_run",
    ])
    lines.append("")

    lines.append("## Current Known Limitations")
    lines.append("")
    lines.append("- Preference candidates are expanded, but many pairs are original-buggy/no-patch vs gold; useful for pipeline checks, not yet rich enough for serious DPO.")
    lines.append("- Current training loop is scaffold/dry-run only; no real SFT/DPO/GRPO has been run.")
    lines.append("- Hidden tests remain evaluator-only and are not model-facing.")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
