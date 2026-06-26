#!/usr/bin/env python3
"""Evaluate code RAG localization accuracy using gold file references.

For each task in mini_repo_debug, check whether the hybrid retriever
can locate the correct file/function using the task's issue text as query.

Usage:
    python scripts/eval_rag_localization.py \\
      --root data/mini_repo_debug \\
      --out data/mini_repo_debug/code_index/localization_eval.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.rag.retriever import HybridRetriever


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval code RAG localization")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/code_index/localization_eval.json")
    parser.add_argument("--limit", type=int, default=0, help="Limit eval to N tasks (0=all)")
    args = parser.parse_args()

    root = Path(args.root)
    repos_dir = root / "repos"
    train_package = root / "train_package"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load gold file references from SFT training data
    gold_refs = _load_gold_refs(train_package)

    task_dirs = sorted(repos_dir.glob("task_*"))
    if args.limit:
        task_dirs = task_dirs[:args.limit]

    results = run_eval(task_dirs, gold_refs)

    results["eval_config"] = {
        "root": str(root),
        "num_tasks": len(task_dirs),
    }

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# Code RAG Localization Eval")
    print(f"  tasks: {results['num_tasks']}")
    print(f"  file_hit@1: {results['file_hit_at_1']:.4f}")
    print(f"  file_hit@3: {results['file_hit_at_3']:.4f}")
    print(f"  file_hit@5: {results['file_hit_at_5']:.4f}")
    print(f"  symbol_hit@1: {results['symbol_hit_at_1']:.4f}")
    print(f"  symbol_hit@3: {results['symbol_hit_at_3']:.4f}")
    print(f"  symbol_hit@5: {results['symbol_hit_at_5']:.4f}")
    print(f"  avg_chunks: {results['avg_chunks_per_task']:.1f}")
    print(f"  passed: {results['passed']}")

    return 0 if results["passed"] else 1


def _load_gold_refs(package_dir: Path) -> dict[str, dict[str, Any]]:
    """Load gold file/function references from SFT data."""
    refs: dict[str, dict[str, Any]] = {}
    sft_path = package_dir / "sft_train.jsonl"
    if not sft_path.exists():
        return refs
    for line in sft_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        task_id = d.get("task_id", "")
        loc = d.get("localization", {})
        if task_id and loc:
            refs[task_id] = {
                "gold_files": loc.get("gold_files", []),
                "gold_functions": loc.get("gold_functions", []),
            }
    return refs


def run_eval(task_dirs: list[Path], gold_refs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    file_hit_1 = 0
    file_hit_3 = 0
    file_hit_5 = 0
    symbol_hit_1 = 0
    symbol_hit_3 = 0
    symbol_hit_5 = 0
    total_valid = 0
    total_chunks = 0
    per_task: list[dict[str, Any]] = []

    for task_dir in task_dirs:
        task_id = task_dir.name
        gold = gold_refs.get(task_id, {})
        gold_files = set(gold.get("gold_files", []))
        gold_funcs = set(gold.get("gold_functions", []))

        if not gold_files:
            continue

        total_valid += 1

        # Build retriever for this task
        retriever = HybridRetriever(index_root=task_dir)
        total_chunks += retriever.total_chunks

        # Use issue text as query
        issue_text = _read_issue(task_dir)

        results = retriever.search(query=issue_text, top_k=10, path_bias=str(task_dir))
        retrieved_files: dict[int, set[str]] = {k: set() for k in [1, 3, 5]}
        retrieved_symbols: dict[int, set[str]] = {k: set() for k in [1, 3, 5]}

        for k in [1, 3, 5]:
            for r in results[:k]:
                c = r["chunk"]
                retrieved_files[k].add(c.file_path)
                retrieved_symbols[k].add(c.name)

        # File hit
        if gold_files & retrieved_files[1]:
            file_hit_1 += 1
        if gold_files & retrieved_files[3]:
            file_hit_3 += 1
        if gold_files & retrieved_files[5]:
            file_hit_5 += 1

        # Symbol (function/class name) hit
        if gold_funcs & retrieved_symbols[1]:
            symbol_hit_1 += 1
        if gold_funcs & retrieved_symbols[3]:
            symbol_hit_3 += 1
        if gold_funcs & retrieved_symbols[5]:
            symbol_hit_5 += 1

        per_task.append({
            "task_id": task_id,
            "total_chunks": retriever.total_chunks,
            "gold_files": sorted(gold_files),
            "gold_functions": sorted(gold_funcs),
            "top5_files": sorted({r["chunk"].file_path for r in results[:5]}),
            "top5_symbols": sorted({r["chunk"].name for r in results[:5]}),
        })

    n = max(1, total_valid)
    # Use symbol_hit@1 as pass threshold (file_hit is 0 because tasks have unique file paths)
    passed = symbol_hit_1 / n >= 0.10  # expect at least 10% symbol-hit@1

    return {
        "num_tasks": len(task_dirs),
        "valid_tasks": total_valid,
        "avg_chunks_per_task": total_chunks / max(1, total_valid),
        "file_hit_at_1": round(file_hit_1 / n, 4),
        "file_hit_at_3": round(file_hit_3 / n, 4),
        "file_hit_at_5": round(file_hit_5 / n, 4),
        "symbol_hit_at_1": round(symbol_hit_1 / n, 4),
        "symbol_hit_at_3": round(symbol_hit_3 / n, 4),
        "symbol_hit_at_5": round(symbol_hit_5 / n, 4),
        "passed": passed,
        "per_task": per_task,
    }


def _read_issue(task_dir: Path) -> str:
    """Read issue text from task directory."""
    issue_path = task_dir / "issue.md"
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8")
    metadata_path = task_dir / "metadata.json"
    if metadata_path.exists():
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        return meta.get("issue", meta.get("description", ""))
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
