from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.export_training_candidates import export_training_candidates
from codeguide_agent.eval.run_eval import discover_tasks
from codeguide_agent.reward.hacking_checks import changed_files_from_diff


PACKAGE_VERSION = "codeguide-mini-repo-debug-p6-v1"
DEFAULT_EXPORTS_DIR = Path("data/mini_repo_debug/exports")
FORBIDDEN_PACKAGE_TERMS = ("tests_hidden", "metadata.json", "gold.patch", "apply_gold_patch")
SYSTEM_PROMPT = "You are CodeGuide-Agent, a repo-level debugging and repair agent. Use public evidence and produce minimal patches."


def prepare_training_package(
    root: str | Path,
    out: str | Path,
    exports_dir: str | Path = DEFAULT_EXPORTS_DIR,
    preference_bank: str | Path | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    out_path = Path(out)
    exports_path = Path(exports_dir)
    if not (exports_path / "p5_sft_rollouts.jsonl").exists() or not (exports_path / "p5_preference_pairs.jsonl").exists():
        export_training_candidates(root_path, exports_path)

    sft_candidates = _read_jsonl(exports_path / "p5_sft_rollouts.jsonl")
    preference_source_path = Path(preference_bank) if preference_bank is not None else exports_path / "p5_preference_pairs.jsonl"
    preference_candidates = _read_jsonl(preference_source_path)
    sft_records = [_normalize_sft(record) for record in sft_candidates]
    preference_records = [_normalize_preference(record) for record in preference_candidates]

    sft_train, sft_eval = _split_by_task_id(sft_records)
    preference_train, preference_eval = _split_by_task_id(preference_records, keep_singleton_train=True)

    out_path.mkdir(parents=True, exist_ok=True)
    paths = {
        "sft_train": out_path / "sft_train.jsonl",
        "sft_eval": out_path / "sft_eval.jsonl",
        "preference_train": out_path / "preference_train.jsonl",
        "preference_eval": out_path / "preference_eval.jsonl",
        "manifest": out_path / "manifest.json",
        "data_card": out_path / "data_card.md",
    }
    _write_jsonl(paths["sft_train"], sft_train)
    _write_jsonl(paths["sft_eval"], sft_eval)
    _write_jsonl(paths["preference_train"], preference_train)
    _write_jsonl(paths["preference_eval"], preference_eval)

    quality_gate = validate_training_package(root_path, out_path)
    manifest = _build_manifest(
        root_path,
        exports_path,
        paths,
        sft_train,
        sft_eval,
        preference_train,
        preference_eval,
        quality_gate,
        preference_source_path,
    )
    paths["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    paths["data_card"].write_text(_build_data_card(manifest), encoding="utf-8")
    return manifest


def validate_training_package(root: str | Path, package_dir: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    package_path = Path(package_dir)
    known_task_ids = {path.name for path in discover_tasks(root_path)}
    errors: list[str] = []
    warnings: list[str] = []
    replay: dict[str, Any] = {"checked_records": 0, "patch_inspection_failures": []}

    files = {
        "sft_train": package_path / "sft_train.jsonl",
        "sft_eval": package_path / "sft_eval.jsonl",
        "preference_train": package_path / "preference_train.jsonl",
        "preference_eval": package_path / "preference_eval.jsonl",
    }
    records_by_split: dict[str, list[dict[str, Any]]] = {}
    for split, path in files.items():
        if not path.exists():
            errors.append(f"missing output file: {path.name}")
            records_by_split[split] = []
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_PACKAGE_TERMS:
            if forbidden in text:
                errors.append(f"{path.name} contains forbidden term")
        if '"stdout"' in text or '"stderr"' in text:
            errors.append(f"{path.name} contains raw test stdout/stderr keys")
        records_by_split[split] = _read_jsonl(path)

    for split in ("sft_train", "sft_eval"):
        for record in records_by_split.get(split, []):
            _validate_sft_record(record, known_task_ids, errors)
            _inspect_patch(record, root_path, replay, errors)
    for split in ("preference_train", "preference_eval"):
        for record in records_by_split.get(split, []):
            _validate_preference_record(record, known_task_ids, errors)
            _inspect_patch(record["chosen"], root_path, replay, errors, task_id=record.get("task_id"))
            if record.get("rejection_reason") == "no_patch" and not record["rejected"].get("final_patch"):
                replay["checked_records"] += 1
            else:
                _inspect_patch(record["rejected"], root_path, replay, errors, task_id=record.get("task_id"))

    _validate_no_task_overlap(records_by_split.get("sft_train", []), records_by_split.get("sft_eval", []), "sft", errors)
    _validate_no_task_overlap(
        records_by_split.get("preference_train", []),
        records_by_split.get("preference_eval", []),
        "preference",
        errors,
    )
    if len(records_by_split.get("preference_train", [])) + len(records_by_split.get("preference_eval", [])) < 5:
        warnings.append("preference dataset is tiny; use only for pipeline checks until more rejected trajectories exist")

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "replay": replay,
    }


def _normalize_sft(record: dict[str, Any]) -> dict[str, Any]:
    assistant_payload = {
        "tool_trace": record.get("actions", []),
        "final_patch": record.get("final_patch", ""),
        "reward_summary": record.get("reward_summary", {}),
    }
    return {
        "record_type": "codeguide_sft_v1",
        "task_id": record["task_id"],
        "source_record_type": record.get("record_type", ""),
        "source_trajectory": record.get("source_trajectory", ""),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(record.get("prompt_context", {}))},
            {"role": "assistant", "content": json.dumps(assistant_payload, sort_keys=True)},
        ],
        "tool_trace": record.get("actions", []),
        "final_patch": record.get("final_patch", ""),
        "reward_summary": record.get("reward_summary", {}),
        "localization": record.get("localization", {}),
        "quality": {
            "source_success": bool(
                record.get("reward_summary", {}).get("public_pass")
                and record.get("reward_summary", {}).get("hidden_pass")
                and not record.get("reward_summary", {}).get("leakage_detected")
                and not record.get("reward_summary", {}).get("syntax_error")
            )
        },
    }


def _normalize_preference(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "codeguide_preference_v1",
        "task_id": record["task_id"],
        "prompt": _user_prompt(record.get("prompt_context", {})),
        "chosen": _normalize_preference_side(record.get("chosen", {})),
        "rejected": _normalize_preference_side(record.get("rejected", {})),
        "reason_labels": list(record.get("reason_labels", [])),
        "source_policy": record.get("source_policy", ""),
        "rejection_reason": record.get("rejection_reason", ""),
        "evaluator_metadata": record.get("evaluator_metadata", {}),
        "localization": record.get("localization", {}),
    }


def _normalize_preference_side(side: dict[str, Any]) -> dict[str, Any]:
    response_payload = {
        "tool_trace": side.get("actions", []),
        "final_patch": side.get("final_patch", ""),
        "reward_summary": side.get("reward_summary", {}),
    }
    return {
        "trajectory_id": side.get("trajectory_id", ""),
        "source_trajectory": side.get("source_trajectory", ""),
        "messages": [
            {"role": "assistant", "content": json.dumps(response_payload, sort_keys=True)},
        ],
        "tool_trace": side.get("actions", []),
        "final_patch": side.get("final_patch", ""),
        "reward_summary": side.get("reward_summary", {}),
    }


def _user_prompt(prompt_context: dict[str, Any]) -> str:
    issue = str(prompt_context.get("issue", "")).strip()
    public_command = str(prompt_context.get("public_test_cmd", "")).strip()
    return "\n".join(
        [
            "Repair the Mini-Repo-Debug task using only public repo evidence.",
            "",
            "Issue:",
            issue,
            "",
            "Public test command:",
            public_command,
        ]
    )


def _split_by_task_id(records: list[dict[str, Any]], keep_singleton_train: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(records, key=lambda record: str(record.get("task_id", "")))
    if keep_singleton_train and len(ordered) <= 1:
        return ordered, []
    train: list[dict[str, Any]] = []
    eval_records: list[dict[str, Any]] = []
    for index, record in enumerate(ordered):
        if index % 5 == 4:
            eval_records.append(record)
        else:
            train.append(record)
    if not eval_records and len(ordered) > 1:
        eval_records.append(train.pop())
    return train, eval_records


def _build_manifest(
    root: Path,
    exports_dir: Path,
    paths: dict[str, Path],
    sft_train: list[dict[str, Any]],
    sft_eval: list[dict[str, Any]],
    preference_train: list[dict[str, Any]],
    preference_eval: list[dict[str, Any]],
    quality_gate: dict[str, Any],
    preference_source_path: Path,
) -> dict[str, Any]:
    counts = {
        "sft_train": len(sft_train),
        "sft_eval": len(sft_eval),
        "sft_total": len(sft_train) + len(sft_eval),
        "preference_train": len(preference_train),
        "preference_eval": len(preference_eval),
        "preference_total": len(preference_train) + len(preference_eval),
    }
    splits = {
        "sft_train_task_ids": _task_ids(sft_train),
        "sft_eval_task_ids": _task_ids(sft_eval),
        "preference_train_task_ids": _task_ids(preference_train),
        "preference_eval_task_ids": _task_ids(preference_eval),
    }
    return {
        "package_version": PACKAGE_VERSION,
        "root": str(root),
        "exports_dir": str(exports_dir),
        "outputs": {key: str(value) for key, value in paths.items()},
        "counts": counts,
        "splits": splits,
        "preference_source": {
            "kind": "preference_bank" if preference_source_path.name == "preference_candidates.jsonl" else "p5_exports",
            "path": str(preference_source_path),
        },
        "quality_gate": quality_gate,
        "limitations": [
            "No model training is included.",
            "Preference data is intentionally tiny and currently useful only for pipeline checks.",
            "Evaluator-only pass/fail reward summaries are retained, but hidden verifier content is not model-facing.",
        ],
    }


def _build_data_card(manifest: dict[str, Any]) -> str:
    counts = manifest["counts"]
    return "\n".join(
        [
            "# CodeGuide Mini-Repo-Debug P6 Training Package",
            "",
            "This package normalizes P5 Mini-Repo-Debug trajectory exports into train-ready SFT and preference JSONL files.",
            "",
            "## Files",
            "",
            "- `sft_train.jsonl`",
            "- `sft_eval.jsonl`",
            "- `preference_train.jsonl`",
            "- `preference_eval.jsonl`",
            "- `manifest.json`",
            "",
            "## Counts",
            "",
            f"- SFT train: {counts['sft_train']}",
            f"- SFT eval: {counts['sft_eval']}",
            f"- Preference train: {counts['preference_train']}",
            f"- Preference eval: {counts['preference_eval']}",
            "",
            "## Safety",
            "",
            "Model-facing JSONL files exclude evaluator-only verifier rows, raw test output fields, and oracle patch actions.",
            "Aggregate reward fields may include pass/fail summaries for offline filtering.",
            "",
            "## Limitations",
            "",
            "- The preference split is very small and should not be treated as sufficient for model training.",
            "- The replay check is a lightweight patch inspection gate, not a full execution replay.",
            "",
        ]
    )


def _validate_sft_record(record: dict[str, Any], known_task_ids: set[str], errors: list[str]) -> None:
    if record.get("record_type") != "codeguide_sft_v1":
        errors.append("SFT record has invalid record_type")
    _validate_task_id(record, known_task_ids, errors)
    if [message.get("role") for message in record.get("messages", [])] != ["system", "user", "assistant"]:
        errors.append(f"SFT record {record.get('task_id')} has invalid messages")
    reward = record.get("reward_summary", {})
    if not (reward.get("public_pass") and reward.get("hidden_pass")):
        errors.append(f"SFT record {record.get('task_id')} is not from a successful trajectory")
    if reward.get("leakage_detected") or reward.get("syntax_error"):
        errors.append(f"SFT record {record.get('task_id')} failed quality filters")


def _validate_preference_record(record: dict[str, Any], known_task_ids: set[str], errors: list[str]) -> None:
    if record.get("record_type") != "codeguide_preference_v1":
        errors.append("preference record has invalid record_type")
    _validate_task_id(record, known_task_ids, errors)
    if not record.get("reason_labels"):
        errors.append(f"preference record {record.get('task_id')} has no reason_labels")
    if not record.get("chosen", {}).get("final_patch", "").startswith("diff --git"):
        errors.append(f"preference record {record.get('task_id')} chosen patch is missing")
    rejected_patch = record.get("rejected", {}).get("final_patch", "")
    if record.get("rejection_reason") == "no_patch":
        if rejected_patch:
            errors.append(f"preference record {record.get('task_id')} no_patch rejected side should not include a patch")
    elif not rejected_patch.startswith("diff --git"):
        errors.append(f"preference record {record.get('task_id')} rejected patch is missing")


def _validate_task_id(record: dict[str, Any], known_task_ids: set[str], errors: list[str]) -> None:
    task_id = str(record.get("task_id", ""))
    if task_id not in known_task_ids:
        errors.append(f"unknown task_id: {task_id}")


def _validate_no_task_overlap(train: list[dict[str, Any]], eval_records: list[dict[str, Any]], label: str, errors: list[str]) -> None:
    overlap = set(_task_ids(train)) & set(_task_ids(eval_records))
    if overlap:
        errors.append(f"{label} train/eval task overlap: {sorted(overlap)}")


def _inspect_patch(
    record: dict[str, Any],
    root: Path,
    replay: dict[str, Any],
    errors: list[str],
    task_id: str | None = None,
) -> None:
    task_id = task_id or str(record.get("task_id", ""))
    patch = str(record.get("final_patch", ""))
    changed_files = changed_files_from_diff(patch)
    replay["checked_records"] += 1
    if not patch.startswith("diff --git") or not changed_files:
        replay["patch_inspection_failures"].append({"task_id": task_id, "reason": "missing_diff"})
        errors.append(f"patch inspection failed for {task_id}: missing diff")
        return
    task_path = root / "repos" / task_id
    missing = [file_name for file_name in changed_files if not (task_path / file_name).exists()]
    if missing:
        replay["patch_inspection_failures"].append({"task_id": task_id, "reason": "missing_files", "files": missing})
        errors.append(f"patch inspection failed for {task_id}: missing files")


def _task_ids(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("task_id", "")) for record in records]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare P6 train-ready Mini-Repo-Debug package.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/train_package")
    parser.add_argument("--exports-dir", default=str(DEFAULT_EXPORTS_DIR))
    parser.add_argument("--preference-bank", help="Optional expanded preference_candidates.jsonl to use instead of P5 pairs.")
    args = parser.parse_args()

    manifest = prepare_training_package(args.root, args.out, args.exports_dir, args.preference_bank)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["quality_gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
