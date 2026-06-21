from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.prepare_training_package import validate_training_package


FORBIDDEN_MODEL_TERMS = ("tests_hidden", "metadata.json", "gold.patch", "apply_gold_patch")


@dataclass
class LoadedTrainingPackage:
    mode: str
    package_dir: Path
    train_records: list[dict[str, Any]]
    eval_records: list[dict[str, Any]]
    batch_size: int
    quality_gate: dict[str, Any]
    preview_batch: list[dict[str, Any]]

    @property
    def batch_count(self) -> int:
        return math.ceil(len(self.train_records) / self.batch_size) if self.batch_size > 0 else 0


def load_training_package(
    package_dir: str | Path,
    mode: str,
    batch_size: int = 4,
    root: str | Path = "data/mini_repo_debug",
) -> LoadedTrainingPackage:
    if mode not in {"sft", "preference"}:
        raise ValueError("mode must be 'sft' or 'preference'")
    package_path = Path(package_dir)
    _assert_sanitized(package_path, mode)
    quality_gate = validate_training_package(root, package_path)
    if not quality_gate.get("passed"):
        raise ValueError(f"training package quality gate failed: {quality_gate.get('errors')}")

    if mode == "sft":
        train_records = _read_jsonl(package_path / "sft_train.jsonl")
        eval_records = _read_jsonl(package_path / "sft_eval.jsonl")
        _validate_sft_records(train_records + eval_records)
    else:
        train_records = _read_jsonl(package_path / "preference_train.jsonl")
        eval_records = _read_jsonl(package_path / "preference_eval.jsonl")
        _validate_preference_records(train_records + eval_records)

    return LoadedTrainingPackage(
        mode=mode,
        package_dir=package_path,
        train_records=train_records,
        eval_records=eval_records,
        batch_size=batch_size,
        quality_gate=quality_gate,
        preview_batch=train_records[:batch_size],
    )


def format_sft_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": record["task_id"],
        "messages": record["messages"],
        "final_patch": record["final_patch"],
        "reward_summary": record.get("reward_summary", {}),
    }


def format_preference_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": record["task_id"],
        "prompt": record["prompt"],
        "chosen": record["chosen"]["messages"],
        "rejected": record["rejected"]["messages"],
        "reason_labels": record.get("reason_labels", []),
    }


def _validate_sft_records(records: list[dict[str, Any]]) -> None:
    for record in records:
        if record.get("record_type") != "codeguide_sft_v1":
            raise ValueError(f"invalid SFT record_type for {record.get('task_id')}")
        roles = [message.get("role") for message in record.get("messages", [])]
        if roles != ["system", "user", "assistant"]:
            raise ValueError(f"invalid SFT messages for {record.get('task_id')}")
        reward = record.get("reward_summary", {})
        if not (reward.get("public_pass") and reward.get("hidden_pass")):
            raise ValueError(f"SFT record is not successful: {record.get('task_id')}")


def _validate_preference_records(records: list[dict[str, Any]]) -> None:
    for record in records:
        if record.get("record_type") != "codeguide_preference_v1":
            raise ValueError(f"invalid preference record_type for {record.get('task_id')}")
        if not record.get("reason_labels"):
            raise ValueError(f"preference record missing reason_labels: {record.get('task_id')}")
        if "chosen" not in record or "rejected" not in record:
            raise ValueError(f"preference record missing chosen/rejected: {record.get('task_id')}")


def _assert_sanitized(package_path: Path, mode: str) -> None:
    names = ["sft_train.jsonl", "sft_eval.jsonl"] if mode == "sft" else ["preference_train.jsonl", "preference_eval.jsonl"]
    for name in names:
        text = (package_path / name).read_text(encoding="utf-8")
        for term in FORBIDDEN_MODEL_TERMS:
            if term in text:
                raise ValueError(f"forbidden model-facing term found in {name}: {term}")
        if '"stdout"' in text or '"stderr"' in text:
            raise ValueError(f"raw stdout/stderr key found in {name}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
