#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cuda_info() -> dict:
    if not has_module("torch"):
        return {"torch_installed": False, "cuda_available": False}
    import torch
    return {
        "torch_installed": True,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
    }


def run_ok(cmd: list[str]) -> bool:
    try:
        subprocess.check_call(cmd)
        return True
    except Exception:
        return False


def main() -> None:
    data = Path("data/mini_repo_debug/hf_training")
    train = read_jsonl(data / "sft_train.jsonl")
    eval_ = read_jsonl(data / "sft_eval.jsonl")
    dpo = read_jsonl(data / "dpo_train.jsonl")

    deps = {
        "torch": has_module("torch"),
        "transformers": has_module("transformers"),
        "datasets": has_module("datasets"),
        "peft": has_module("peft"),
        "trl": has_module("trl"),
        "accelerate": has_module("accelerate"),
        "bitsandbytes": has_module("bitsandbytes"),
    }

    checks = {
        "hf_training_data_exists": data.exists(),
        "sft_train_non_empty": len(train) > 0,
        "sft_eval_non_empty": len(eval_) > 0,
        "dpo_train_non_empty": len(dpo) > 0,
        "core_deps_installed": all(deps[k] for k in ["torch", "transformers", "datasets", "peft"]),
        "cuda_available": cuda_info().get("cuda_available", False),
        "clean_check_passed": run_ok(["make", "clean-check"]),
    }

    smoke_sft_ready = (
        checks["hf_training_data_exists"]
        and checks["sft_train_non_empty"]
        and checks["core_deps_installed"]
    )

    real_training_recommended = (
        smoke_sft_ready
        and len(train) >= 150
        and len(dpo) >= 100
    )

    report = {
        "deps": deps,
        "cuda": cuda_info(),
        "sft_train": len(train),
        "sft_eval": len(eval_),
        "dpo_train": len(dpo),
        "checks": checks,
        "smoke_sft_ready": smoke_sft_ready,
        "real_training_recommended": real_training_recommended,
        "decision": "SMOKE_READY" if smoke_sft_ready else "NOT_READY",
        "note": "Smoke SFT can run with current data once dependencies/model/GPU are available. Meaningful training still requires dataset expansion.",
    }

    Path("docs/TRAINING_PREFLIGHT_REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("# Training Preflight")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not smoke_sft_ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
