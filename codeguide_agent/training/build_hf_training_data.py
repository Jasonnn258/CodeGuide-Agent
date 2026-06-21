from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def render_messages(messages: list[dict[str, str]]) -> str:
    chunks: list[str] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        chunks.append(f"<|{role}|>\n{content}")
    chunks.append("<|end|>")
    return "\n".join(chunks)


def build_sft(package: Path, out: Path) -> dict[str, int]:
    train = read_jsonl(package / "sft_train.jsonl")
    eval_ = read_jsonl(package / "sft_eval.jsonl")

    def convert(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": row.get("task_id"),
            "text": render_messages(row.get("messages", [])),
            "final_patch": row.get("final_patch", ""),
            "source": "codeguide_sft_v1",
        }

    train_rows = [convert(row) for row in train]
    eval_rows = [convert(row) for row in eval_]

    write_jsonl(out / "sft_train.jsonl", train_rows)
    write_jsonl(out / "sft_eval.jsonl", eval_rows)

    return {"sft_train": len(train_rows), "sft_eval": len(eval_rows), "sft_total": len(train_rows) + len(eval_rows)}


def build_dpo(package: Path, out: Path) -> dict[str, int]:
    train = read_jsonl(package / "preference_train.jsonl")
    eval_ = read_jsonl(package / "preference_eval.jsonl")

    def prompt_from_row(row: dict[str, Any]) -> str:
        ctx = row.get("prompt_context", {})
        issue = ctx.get("issue", "")
        public_cmd = ctx.get("public_test_cmd", "")
        return (
            "<|system|>\n"
            "You are CodeGuide, a coding agent that fixes small Python repositories.\n"
            "<|user|>\n"
            f"Issue:\n{issue}\n\n"
            f"Public test command:\n{public_cmd}\n\n"
            "Return a minimal unified git diff patch."
        )

    def convert(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": row.get("task_id"),
            "prompt": prompt_from_row(row),
            "chosen": row.get("chosen", {}).get("final_patch", ""),
            "rejected": row.get("rejected", {}).get("final_patch", ""),
            "reason_labels": row.get("reason_labels", []),
            "source": "codeguide_preference_v1",
        }

    train_rows = [convert(row) for row in train]
    eval_rows = [convert(row) for row in eval_]

    write_jsonl(out / "dpo_train.jsonl", train_rows)
    write_jsonl(out / "dpo_eval.jsonl", eval_rows)

    return {"dpo_train": len(train_rows), "dpo_eval": len(eval_rows), "dpo_total": len(train_rows) + len(eval_rows)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default="data/mini_repo_debug/train_package")
    parser.add_argument("--out", default="data/mini_repo_debug/hf_training")
    args = parser.parse_args()

    package = Path(args.package)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sft_counts = build_sft(package, out)
    dpo_counts = build_dpo(package, out)

    manifest = {
        "package": str(package),
        "out": str(out),
        **sft_counts,
        **dpo_counts,
        "note": "HF-style files are training inputs. Current data is suitable for smoke training, not final performance claims.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
