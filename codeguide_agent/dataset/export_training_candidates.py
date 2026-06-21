from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.eval.run_eval import discover_tasks


DEFAULT_TRAJECTORIES_DIR = Path("data/mini_repo_debug/trajectories")
FORBIDDEN_EXPORT_TERMS = ("tests_hidden", "metadata.json", "gold.patch")
REWARD_KEYS = (
    "public_pass",
    "hidden_pass",
    "public_pass_hidden_fail",
    "hidden_failure_type",
    "patch_generalization_risk",
    "patch_too_narrow",
    "leakage_detected",
    "forbidden_file_access",
    "oracle_metadata_leakage",
    "syntax_error",
    "gold_file_hit_at_3",
    "gold_function_hit_at_3",
    "gold_file_patched",
    "gold_function_patched",
    "changed_lines_count",
    "invalid_action_count",
    "total_reward",
)


def load_trajectory(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def export_training_candidates(
    root: str | Path,
    out: str | Path,
    trajectories_dir: str | Path = DEFAULT_TRAJECTORIES_DIR,
) -> dict[str, Any]:
    root_path = Path(root)
    out_path = Path(out)
    trajectories_path = Path(trajectories_dir)
    tasks = discover_tasks(root_path)
    out_path.mkdir(parents=True, exist_ok=True)

    sft_records: list[dict[str, Any]] = []
    preference_pairs: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    rollout_sft_task_ids: set[str] = set()

    for task_path in tasks:
        metadata = load_metadata(task_path)
        task_id = metadata["task_id"]
        llm_path = trajectories_path / f"{task_id}_llm.jsonl"
        gold_path = trajectories_path / f"{task_id}_gold.jsonl"
        if not llm_path.exists():
            skipped["missing_llm_trajectory"] = skipped.get("missing_llm_trajectory", 0) + 1
            continue

        llm_rows = load_trajectory(llm_path)
        llm_final = _final_row(llm_rows)
        if not llm_final:
            skipped["missing_llm_final"] = skipped.get("missing_llm_final", 0) + 1
            continue
        llm_reward = llm_final.get("reward", {})

        if _is_successful_llm_candidate(llm_reward):
            sft_records.append(_build_sft_record(task_path, metadata, llm_path, llm_rows, llm_final))
            rollout_sft_task_ids.add(task_id)
        elif _is_rejected_candidate(llm_reward) and gold_path.exists():
            gold_rows = load_trajectory(gold_path)
            gold_final = _final_row(gold_rows)
            if gold_final:
                preference_pairs.append(
                    _build_preference_pair(task_path, metadata, llm_path, llm_rows, llm_final, gold_path, gold_rows, gold_final)
                )

    gold_sft_records: list[dict[str, Any]] = []
    for task_path in tasks:
        metadata = load_metadata(task_path)
        if _is_train_split(metadata) and metadata["task_id"] not in rollout_sft_task_ids:
            gold_sft_records.append(_build_gold_patch_sft_record(task_path, metadata))
    sft_records.extend(gold_sft_records)

    sft_output = out_path / "p5_sft_rollouts.jsonl"
    preference_output = out_path / "p5_preference_pairs.jsonl"
    summary_output = out_path / "p5_export_summary.json"
    _write_jsonl(sft_output, sft_records)
    _write_jsonl(preference_output, preference_pairs)
    summary = {
        "root": str(root_path),
        "trajectories_dir": str(trajectories_path),
        "sft_output": str(sft_output),
        "preference_output": str(preference_output),
        "summary_output": str(summary_output),
        "tasks_seen": len(tasks),
        "sft_records": len(sft_records),
        "rollout_sft_records": len(rollout_sft_task_ids),
        "gold_patch_sft_records": len(gold_sft_records),
        "preference_pairs": len(preference_pairs),
        "sft_task_ids": [record["task_id"] for record in sft_records],
        "gold_patch_sft_task_ids": [record["task_id"] for record in gold_sft_records],
        "preference_task_ids": [record["task_id"] for record in preference_pairs],
        "task_009_preference_pair_generated": any(record["task_id"] == "task_009" for record in preference_pairs),
        "skipped": skipped,
        "sanitization": {
            "hidden_verifier_rows_dropped": True,
            "raw_test_stdout_stderr_exported": False,
            "forbidden_path_terms_redacted": len(FORBIDDEN_EXPORT_TERMS),
        },
    }
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def sanitize_trajectory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for row in rows:
        if row.get("type") != "step":
            continue
        if _is_hidden_step(row):
            continue
        if row.get("action_name") == "apply_gold_patch":
            continue
        sanitized.append(_sanitize_step(row))
    return sanitized


def _build_sft_record(
    task_path: Path,
    metadata: dict[str, Any],
    source_path: Path,
    rows: list[dict[str, Any]],
    final: dict[str, Any],
) -> dict[str, Any]:
    reward = final.get("reward", {})
    return {
        "record_type": "sft_rollout_candidate",
        "task_id": metadata["task_id"],
        "trajectory_id": final.get("trajectory_id", ""),
        "source_trajectory": str(source_path),
        "prompt_context": _prompt_context(task_path, metadata),
        "actions": sanitize_trajectory_rows(rows),
        "final_patch": _sanitize_text(final.get("final_patch", "")),
        "reward_summary": _reward_summary(reward),
        "localization": _localization_summary(metadata, reward),
    }


def _build_gold_patch_sft_record(task_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    patch_path = task_path / metadata.get("gold_patch", "gold.patch")
    reward = {
        "public_pass": True,
        "hidden_pass": True,
        "public_pass_hidden_fail": False,
        "hidden_failure_type": "none",
        "patch_generalization_risk": "low",
        "patch_too_narrow": False,
        "leakage_detected": False,
        "forbidden_file_access": False,
        "oracle_metadata_leakage": False,
        "syntax_error": False,
        "gold_file_patched": True,
        "gold_function_patched": True,
    }
    return {
        "record_type": "gold_patch_sft_candidate",
        "source": "gold_patch",
        "task_id": metadata["task_id"],
        "target_files": list(metadata.get("gold_files", [])),
        "gold_functions": list(metadata.get("gold_functions", [])),
        "prompt_context": _prompt_context(task_path, metadata),
        "actions": [],
        "final_patch": _sanitize_text(patch_path.read_text(encoding="utf-8")),
        "reward_summary": _reward_summary(reward),
        "localization": _localization_summary(metadata, reward),
    }


def _build_preference_pair(
    task_path: Path,
    metadata: dict[str, Any],
    rejected_path: Path,
    rejected_rows: list[dict[str, Any]],
    rejected_final: dict[str, Any],
    chosen_path: Path,
    chosen_rows: list[dict[str, Any]],
    chosen_final: dict[str, Any],
) -> dict[str, Any]:
    rejected_reward = rejected_final.get("reward", {})
    chosen_reward = chosen_final.get("reward", {})
    return {
        "record_type": "preference_pair_candidate",
        "task_id": metadata["task_id"],
        "prompt_context": _prompt_context(task_path, metadata),
        "rejected": {
            "trajectory_id": rejected_final.get("trajectory_id", ""),
            "source_trajectory": str(rejected_path),
            "actions": sanitize_trajectory_rows(rejected_rows),
            "final_patch": _sanitize_text(rejected_final.get("final_patch", "")),
            "reward_summary": _reward_summary(rejected_reward),
        },
        "chosen": {
            "trajectory_id": chosen_final.get("trajectory_id", ""),
            "source_trajectory": str(chosen_path),
            "actions": sanitize_trajectory_rows(chosen_rows),
            "final_patch": _sanitize_text(chosen_final.get("final_patch", "")),
            "reward_summary": _reward_summary(chosen_reward),
        },
        "reason_labels": _reason_labels(rejected_reward),
        "localization": _localization_summary(metadata, rejected_reward),
    }


def _prompt_context(task_path: Path, metadata: dict[str, Any]) -> dict[str, str]:
    issue_path = task_path / metadata.get("issue_path", "issue.md")
    return {
        "issue": _sanitize_text(issue_path.read_text(encoding="utf-8")),
        "public_test_cmd": _sanitize_text(metadata["public_test_cmd"]),
    }


def _sanitize_step(row: dict[str, Any]) -> dict[str, Any]:
    action_name = str(row.get("action_name", ""))
    return {
        "step_id": row.get("step_id"),
        "action_name": action_name,
        "action_input": _sanitize_action_input(action_name, row.get("action_input", {})),
        "observation": _sanitize_observation(action_name, row.get("observation", {})),
    }


def _sanitize_action_input(action_name: str, action_input: Any) -> Any:
    payload = _sanitize_payload(action_input)
    if isinstance(payload, dict) and action_name == "run_test":
        return {
            "command": payload.get("command", ""),
            "phase": payload.get("phase", ""),
        }
    return payload


def _sanitize_observation(action_name: str, observation: Any) -> Any:
    if not isinstance(observation, dict):
        return _sanitize_payload(observation)
    if action_name == "run_test":
        return {
            "tool_name": observation.get("tool_name", "run_test"),
            "status": observation.get("status", ""),
            "exit_code": observation.get("exit_code"),
            "command": _sanitize_text(str(observation.get("command", ""))),
            "pass_count": _count_passed_tests(observation),
            "fail_count": _count_failed_tests(observation),
        }
    if action_name == "repo_tree":
        return {
            "tool_name": observation.get("tool_name", "repo_tree"),
            "status": observation.get("status", ""),
            "entries": _sanitize_payload(observation.get("entries", [])),
        }
    if action_name == "search_repo":
        return {
            "tool_name": observation.get("tool_name", "search_repo"),
            "status": observation.get("status", ""),
            "matches": _sanitize_payload(observation.get("matches", [])),
        }
    if action_name == "read_file":
        return {
            "tool_name": observation.get("tool_name", "read_file"),
            "status": observation.get("status", ""),
            "file": _sanitize_text(str(observation.get("file", ""))),
            "content": _sanitize_text(str(observation.get("content", ""))),
        }
    if action_name == "edit_file":
        return {
            "tool_name": observation.get("tool_name", "edit_file"),
            "status": observation.get("status", ""),
            "file": _sanitize_text(str(observation.get("file", ""))),
            "replacements": observation.get("replacements"),
        }
    if action_name == "git_diff":
        return {
            "tool_name": observation.get("tool_name", "git_diff"),
            "status": observation.get("status", ""),
            "diff": _sanitize_text(str(observation.get("diff", ""))),
        }
    return _sanitize_payload(observation)


def _sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {str(key): _sanitize_payload(value) for key, value in payload.items() if _safe_key(str(key))}
    if isinstance(payload, list):
        return [_sanitize_payload(item) for item in payload]
    if isinstance(payload, str):
        return _sanitize_text(payload)
    return payload


def _sanitize_text(text: str) -> str:
    sanitized = text
    for term in FORBIDDEN_EXPORT_TERMS:
        sanitized = sanitized.replace(term, "[redacted]")
    return sanitized


def _safe_key(key: str) -> bool:
    return key not in {"stdout", "stderr", "hidden_stdout", "hidden_stderr"}


def _reward_summary(reward: dict[str, Any]) -> dict[str, Any]:
    return {key: reward.get(key) for key in REWARD_KEYS if key in reward}


def _localization_summary(metadata: dict[str, Any], reward: dict[str, Any]) -> dict[str, Any]:
    return {
        "gold_files": metadata.get("gold_files", []),
        "gold_functions": metadata.get("gold_functions", []),
        "gold_file_hit_at_3": reward.get("gold_file_hit_at_3"),
        "gold_function_hit_at_3": reward.get("gold_function_hit_at_3"),
        "gold_file_patched": reward.get("gold_file_patched"),
        "gold_function_patched": reward.get("gold_function_patched"),
    }


def _reason_labels(reward: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    if reward.get("public_pass_hidden_fail"):
        labels.append("public_pass_hidden_fail")
    hidden_failure_type = reward.get("hidden_failure_type")
    if hidden_failure_type and hidden_failure_type != "none":
        labels.append(str(hidden_failure_type))
    risk = reward.get("patch_generalization_risk")
    if risk and risk != "low":
        labels.append(f"{risk}_generalization_risk")
    for key in ("invalid_action_count", "syntax_error", "leakage_detected"):
        value = reward.get(key)
        if key == "invalid_action_count" and value:
            labels.append("invalid_action")
        elif key != "invalid_action_count" and value:
            labels.append(key)
    return sorted(set(labels))


def _is_successful_llm_candidate(reward: dict[str, Any]) -> bool:
    return bool(
        reward.get("public_pass")
        and reward.get("hidden_pass")
        and not reward.get("leakage_detected")
        and not reward.get("syntax_error")
    )


def _is_train_split(metadata: dict[str, Any]) -> bool:
    return str(metadata.get("split", "train")) == "train"


def _is_rejected_candidate(reward: dict[str, Any]) -> bool:
    return bool(
        reward
        and not reward.get("leakage_detected")
        and (
            reward.get("public_pass_hidden_fail")
            or not reward.get("public_pass")
            or not reward.get("hidden_pass")
            or reward.get("syntax_error")
            or reward.get("invalid_action_count", 0) > 0
        )
    )


def _is_hidden_step(row: dict[str, Any]) -> bool:
    action_input = row.get("action_input", {})
    text = json.dumps(action_input, sort_keys=True).lower()
    return "tests_hidden" in text or "final_hidden" in text


def _final_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((row for row in reversed(rows) if row.get("type") == "final"), None)


def _count_passed_tests(observation: dict[str, Any]) -> int:
    stdout = str(observation.get("stdout", ""))
    marker = " passed"
    if marker not in stdout:
        return 0
    total = 0
    for token in stdout.split():
        if token.isdigit():
            total += int(token)
    return total


def _count_failed_tests(observation: dict[str, Any]) -> int:
    stdout = str(observation.get("stdout", ""))
    if "FAILED " not in stdout and " failed" not in stdout:
        return 0
    for token in stdout.split():
        if token.isdigit():
            return int(token)
    return 1


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export P5 Mini-Repo-Debug training-data candidates.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/exports")
    parser.add_argument("--trajectories-dir", default=str(DEFAULT_TRAJECTORIES_DIR))
    args = parser.parse_args()

    summary = export_training_candidates(args.root, args.out, args.trajectories_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
