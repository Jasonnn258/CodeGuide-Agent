from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/mini_repo_debug/hf_training")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    train = read_jsonl(data_dir / "dpo_train.jsonl")
    eval_ = read_jsonl(data_dir / "dpo_eval.jsonl")

    report = {
        "dpo_train": len(train),
        "dpo_eval": len(eval_),
        "ready_for_meaningful_dpo": len(train) >= 100,
        "note": "DPO data is structurally prepared. Current preference data is too small for meaningful DPO; expand hard preferences first.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if len(train) < 100:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
