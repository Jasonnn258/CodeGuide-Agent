from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_training_deps() -> None:
    missing = []
    for name in ["torch", "transformers", "datasets", "peft"]:
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    if missing:
        raise SystemExit(
            "Missing training dependencies: "
            + ", ".join(missing)
            + "\nInstall on a GPU machine with: pip install -r requirements-training.txt"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/training/sft_qwen2_5_coder_lora.json")
    parser.add_argument("--model-name", default=os.environ.get("MODEL_NAME", ""))
    parser.add_argument("--output-dir", default=os.environ.get("OUTPUT_DIR", ""))
    parser.add_argument("--max-steps", type=int, default=int(os.environ.get("MAX_STEPS", "0")))
    args = parser.parse_args()

    require_training_deps()

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    cfg = load_json(args.config)
    model_name = args.model_name or cfg["model_name"]
    output_dir = args.output_dir or cfg["output_dir"]
    data_dir = Path(cfg["data_dir"])

    train_rows = read_jsonl(data_dir / "sft_train.jsonl")
    eval_rows = read_jsonl(data_dir / "sft_eval.jsonl")

    if not train_rows:
        raise SystemExit(f"No SFT training rows found under {data_dir}. Run make training-data first.")

    max_seq_length = int(cfg.get("max_seq_length", 2048))

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(row: dict[str, Any]) -> dict[str, Any]:
        return tokenizer(
            row["text"],
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )

    train_ds = Dataset.from_list(train_rows).map(tokenize, remove_columns=list(train_rows[0].keys()))
    eval_ds = Dataset.from_list(eval_rows).map(tokenize, remove_columns=list(eval_rows[0].keys())) if eval_rows else None

    model_kwargs: dict[str, Any] = {"trust_remote_code": True}
    if cfg.get("device_map", "auto"):
        model_kwargs["device_map"] = cfg.get("device_map", "auto")
    if cfg.get("torch_dtype", "auto") == "bf16":
        model_kwargs["torch_dtype"] = torch.bfloat16
    elif cfg.get("torch_dtype", "auto") == "fp16":
        model_kwargs["torch_dtype"] = torch.float16
    else:
        model_kwargs["torch_dtype"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    model.config.pad_token_id = tokenizer.pad_token_id

    if cfg.get("use_lora", True):
        lora_cfg = LoraConfig(
            r=int(cfg.get("lora_r", 16)),
            lora_alpha=int(cfg.get("lora_alpha", 32)),
            lora_dropout=float(cfg.get("lora_dropout", 0.05)),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=cfg.get("target_modules", ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]),
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()

    training_args_kwargs: dict[str, Any] = {
        "output_dir": output_dir,
        "per_device_train_batch_size": int(cfg.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(cfg.get("gradient_accumulation_steps", 8)),
        "learning_rate": float(cfg.get("learning_rate", 2e-4)),
        "num_train_epochs": float(cfg.get("num_train_epochs", 1.0)),
        "logging_steps": int(cfg.get("logging_steps", 1)),
        "save_steps": int(cfg.get("save_steps", 20)),
        "save_total_limit": int(cfg.get("save_total_limit", 2)),
        "report_to": cfg.get("report_to", "none"),
        "bf16": bool(cfg.get("bf16", True)),
        "fp16": bool(cfg.get("fp16", False)),
        "remove_unused_columns": False,
    }
    if args.max_steps > 0:
        training_args_kwargs["max_steps"] = args.max_steps

    training_args = TrainingArguments(**training_args_kwargs)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    summary = {
        "model_name": model_name,
        "output_dir": output_dir,
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "max_steps": args.max_steps,
        "note": "Training completed. With current small data, treat this as a smoke run unless dataset has been expanded.",
    }
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "codeguide_training_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
