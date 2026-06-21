from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.export_training_candidates import (
    load_trajectory,
    sanitize_trajectory_rows,
)
from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.eval.run_eval import discover_tasks
from codeguide_agent.reward.hacking_checks import changed_files_from_diff


DEFAULT_TRAJECTORIES_DIR = Path("data/mini_repo_debug/trajectories")
FORBIDDEN_TERMS = ("tests_hidden", "metadata.json", "gold.patch", "apply_gold_patch")
REJECTION_TAXONOMY = {
    "public_fail": "Patch or trajectory does not pass public tests.",
    "public_pass_hidden_assertion_fail": "Patch passes public tests but fails evaluator-only assertions.",
    "no_patch": "Policy produced no patch or original buggy code is used as the rejected side.",
    "wrong_file": "Patch touches no gold file when that can be inferred.",
    "syntax_error": "Patch introduces syntax or import-time failure.",
    "invalid_action": "Trajectory contains invalid tool/action behavior.",
    "leakage": "Trajectory is excluded from model-facing preference data because evaluator-oracle leakage was detected.",
    "incomplete_stop": "Trajectory stopped before the required final checks.",
    "generalization_risk": "Patch passes public tests but carries medium/high generalization risk.",
}
REWARD_KEYS = (
    "public_pass",
    "hidden_pass",
    "public_pass_hidden_fail",
    "hidden_failure_type",
    "patch_generalization_risk",
    "patch_too_narrow",
    "leakage_detected",
    "syntax_error",
    "invalid_action_count",
    "incomplete_stop",
    "gold_file_patched",
    "gold_function_patched",
    "total_reward",
)


def expand_preference_candidates(
    root: str | Path,
    out: str | Path,
    trajectories_dir: str | Path = DEFAULT_TRAJECTORIES_DIR,
) -> dict[str, Any]:
    root_path = Path(root)
    out_path = Path(out)
    trajectories_path = Path(trajectories_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    for task_path in discover_tasks(root_path):
        metadata = load_metadata(task_path)
        chosen = _gold_chosen_side(task_path)
        if not chosen:
            skipped["missing_gold_patch"] += 1
            continue
        records.append(_original_buggy_pair(task_path, metadata, chosen))
        for policy in ("llm", "noop", "scripted", "heuristic"):
            candidate = _trajectory_pair(task_path, metadata, chosen, trajectories_path, policy)
            if candidate is None:
                skipped[f"missing_or_unusable_{policy}"] += 1
                continue
            records.append(candidate)

    deduped, duplicate_count = _dedupe(records)
    deduped.sort(key=lambda record: (record["task_id"], record["source_policy"], record["rejection_reason"]))
    quality = _validate_bank(root_path, deduped)

    candidates_path = out_path / "preference_candidates.jsonl"
    summary_path = out_path / "preference_bank_summary.json"
    taxonomy_path = out_path / "rejection_taxonomy.json"
    _write_jsonl(candidates_path, deduped)
    taxonomy_path.write_text(json.dumps(REJECTION_TAXONOMY, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "root": str(root_path),
        "trajectories_dir": str(trajectories_path),
        "candidate_output": str(candidates_path),
        "summary_output": str(summary_path),
        "taxonomy_output": str(taxonomy_path),
        "candidate_count": len(deduped),
        "task_coverage": sorted({record["task_id"] for record in deduped}),
        "task_coverage_count": len({record["task_id"] for record in deduped}),
        "rejection_reason_counts": dict(Counter(record["rejection_reason"] for record in deduped)),
        "source_policy_counts": dict(Counter(record["source_policy"] for record in deduped)),
        "dedupe": {
            "input_candidates": len(records),
            "duplicates_removed": duplicate_count,
            "output_candidates": len(deduped),
        },
        "skipped": dict(skipped),
        "quality_gate": quality,
        "sanitization": {
            "passed": quality["passed"],
            "forbidden_path_terms_redacted": len(FORBIDDEN_TERMS),
            "raw_test_stdout_stderr_exported": False,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _original_buggy_pair(task_path: Path, metadata: dict[str, Any], chosen: dict[str, Any]) -> dict[str, Any]:
    return _pair_record(
        task_path=task_path,
        metadata=metadata,
        chosen=chosen,
        rejected={
            "trajectory_id": f"{metadata['task_id']}_original_buggy",
            "source_trajectory": "",
            "actions": [],
            "final_patch": "",
            "reward_summary": _rejected_reward("no_patch"),
        },
        source_policy="original_buggy",
        rejection_reason="no_patch",
    )


def _trajectory_pair(
    task_path: Path,
    metadata: dict[str, Any],
    chosen: dict[str, Any],
    trajectories_path: Path,
    policy: str,
) -> dict[str, Any] | None:
    path = trajectories_path / f"{metadata['task_id']}_{policy}.jsonl"
    if not path.exists():
        return None
    rows = load_trajectory(path)
    final = _final_row(rows)
    if not final:
        return None
    reward = final.get("reward", {})
    if reward.get("leakage_detected"):
        return None
    reason = _rejection_reason(reward, str(final.get("final_patch", "")), metadata)
    if reason is None:
        return None
    rejected = {
        "trajectory_id": final.get("trajectory_id", f"{metadata['task_id']}_{policy}"),
        "source_trajectory": _safe_source_path(path),
        "actions": sanitize_trajectory_rows(rows),
        "final_patch": _sanitize_text(str(final.get("final_patch", ""))),
        "reward_summary": _reward_summary(reward),
    }
    return _pair_record(
        task_path=task_path,
        metadata=metadata,
        chosen=chosen,
        rejected=rejected,
        source_policy=policy,
        rejection_reason=reason,
    )


def _pair_record(
    task_path: Path,
    metadata: dict[str, Any],
    chosen: dict[str, Any],
    rejected: dict[str, Any],
    source_policy: str,
    rejection_reason: str,
) -> dict[str, Any]:
    labels = sorted(set([rejection_reason] + _reason_labels(rejection_reason, rejected.get("reward_summary", {}))))
    rejected_reward = rejected.get("reward_summary", {})
    return {
        "record_type": "preference_pair_candidate",
        "task_id": metadata["task_id"],
        "prompt_context": _prompt_context(task_path, metadata),
        "chosen": chosen,
        "rejected": rejected,
        "source_policy": source_policy,
        "rejection_reason": rejection_reason,
        "reason_labels": labels,
        "evaluator_metadata": {
            "public_pass": bool(rejected_reward.get("public_pass", False)),
            "hidden_pass": bool(rejected_reward.get("hidden_pass", False)),
            "weaker_than_chosen": True,
            "chosen_is_gold": True,
        },
        "localization": {
            "gold_files": metadata.get("gold_files", []),
            "gold_functions": metadata.get("gold_functions", []),
            "gold_file_patched": rejected_reward.get("gold_file_patched"),
            "gold_function_patched": rejected_reward.get("gold_function_patched"),
        },
    }


def _gold_chosen_side(task_path: Path) -> dict[str, Any] | None:
    patch_path = task_path / "gold.patch"
    if not patch_path.exists():
        return None
    patch = _sanitize_text(patch_path.read_text(encoding="utf-8"))
    return {
        "trajectory_id": f"{task_path.name}_gold_reference",
        "source_trajectory": "",
        "actions": [],
        "final_patch": patch,
        "reward_summary": {
            "public_pass": True,
            "hidden_pass": True,
            "leakage_detected": False,
            "syntax_error": False,
            "total_reward": 1.0,
        },
    }


def _rejection_reason(reward: dict[str, Any], patch: str, metadata: dict[str, Any]) -> str | None:
    if reward.get("syntax_error"):
        return "syntax_error"
    if reward.get("invalid_action_count", 0) > 0:
        return "invalid_action"
    if reward.get("incomplete_stop"):
        return "incomplete_stop"
    if not patch.strip():
        return "no_patch"
    if reward.get("public_pass_hidden_fail"):
        if reward.get("hidden_failure_type") == "hidden_assertion_fail":
            return "public_pass_hidden_assertion_fail"
        return "generalization_risk"
    if reward.get("patch_generalization_risk") in {"medium", "high"} and not reward.get("hidden_pass"):
        return "generalization_risk"
    if not reward.get("public_pass"):
        return "public_fail"
    if not reward.get("gold_file_patched") and _touches_non_gold_file(patch, metadata):
        return "wrong_file"
    if reward and not reward.get("hidden_pass"):
        return "generalization_risk"
    return None


def _touches_non_gold_file(patch: str, metadata: dict[str, Any]) -> bool:
    changed = set(changed_files_from_diff(patch))
    gold = set(metadata.get("gold_files", []))
    return bool(changed) and not bool(changed & gold)


def _rejected_reward(reason: str) -> dict[str, Any]:
    return {
        "public_pass": False,
        "hidden_pass": False,
        "public_pass_hidden_fail": False,
        "hidden_failure_type": "public_fail" if reason == "no_patch" else "hidden_unknown",
        "leakage_detected": False,
        "syntax_error": reason == "syntax_error",
        "total_reward": 0.0,
    }


def _reward_summary(reward: dict[str, Any]) -> dict[str, Any]:
    return {key: reward.get(key) for key in REWARD_KEYS if key in reward}


def _reason_labels(reason: str, reward: dict[str, Any]) -> list[str]:
    labels = [reason]
    hidden_failure_type = reward.get("hidden_failure_type")
    if reason == "public_pass_hidden_assertion_fail":
        labels.append("hidden_assertion_fail")
    elif hidden_failure_type and hidden_failure_type != "none":
        labels.append(str(hidden_failure_type))
    risk = reward.get("patch_generalization_risk")
    if risk and risk != "low":
        labels.append(f"{risk}_generalization_risk")
    if reward.get("patch_too_narrow"):
        labels.append("patch_too_narrow")
    return labels


def _prompt_context(task_path: Path, metadata: dict[str, Any]) -> dict[str, str]:
    issue_path = task_path / metadata.get("issue_path", "issue.md")
    return {
        "issue": _sanitize_text(issue_path.read_text(encoding="utf-8")),
        "public_test_cmd": _sanitize_text(str(metadata.get("public_test_cmd", ""))),
    }


def _safe_source_path(path: Path) -> str:
    return _sanitize_text(str(path))


def _sanitize_text(text: str) -> str:
    sanitized = text
    for term in FORBIDDEN_TERMS:
        sanitized = sanitized.replace(term, "[redacted]")
    return sanitized


def _final_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((row for row in reversed(rows) if row.get("type") == "final"), None)


def _dedupe(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, Any]] = []
    duplicates = 0
    for record in records:
        key = (
            record["task_id"],
            record["chosen"]["final_patch"],
            record["rejected"].get("final_patch", ""),
        )
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        output.append(record)
    return output, duplicates


def _validate_bank(root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    known_task_ids = {path.name for path in discover_tasks(root)}
    errors: list[str] = []
    text = "\n".join(json.dumps(record, sort_keys=True) for record in records)
    for term in FORBIDDEN_TERMS:
        if term in text:
            errors.append(f"forbidden term present: {term}")
    if '"stdout"' in text or '"stderr"' in text:
        errors.append("raw test output key present")
    for record in records:
        task_id = record.get("task_id")
        if task_id not in known_task_ids:
            errors.append(f"unknown task_id: {task_id}")
        if record.get("rejection_reason") not in REJECTION_TAXONOMY:
            errors.append(f"unknown rejection_reason: {record.get('rejection_reason')}")
        chosen_patch = record.get("chosen", {}).get("final_patch", "")
        if not str(chosen_patch).startswith("diff --git"):
            errors.append(f"chosen patch missing for {task_id}")
        rejected_patch = record.get("rejected", {}).get("final_patch", "")
        if record.get("rejection_reason") != "no_patch" and not str(rejected_patch).startswith("diff --git"):
            errors.append(f"rejected patch missing for {task_id}")
        if not record.get("evaluator_metadata", {}).get("weaker_than_chosen"):
            errors.append(f"candidate is not marked weaker_than_chosen: {task_id}")
    return {"passed": not errors, "errors": errors}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand safe Mini-Repo-Debug preference candidates.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/preference_bank")
    parser.add_argument("--trajectories-dir", default=str(DEFAULT_TRAJECTORIES_DIR))
    args = parser.parse_args()

    summary = expand_preference_candidates(args.root, args.out, args.trajectories_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["quality_gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
