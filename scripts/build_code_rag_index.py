#!/usr/bin/env python3
"""Build hybrid code RAG index from Mini-Repo-Debug repositories.

Usage:
    python scripts/build_code_rag_index.py \\
      --root data/mini_repo_debug \\
      --out data/mini_repo_debug/code_index
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.rag.chunking import chunk_directory
from codeguide_agent.rag.code_index import HybridCodeIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Build hybrid code RAG index")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/code_index")
    parser.add_argument("--task-id", default=None, help="Index a single task")
    args = parser.parse_args()

    root = Path(args.root)
    repos_dir = root / "repos"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.task_id:
        task_dirs = [repos_dir / args.task_id]
    else:
        task_dirs = sorted(repos_dir.glob("task_*"))

    index = HybridCodeIndex()
    per_task_stats: dict[str, dict] = {}

    for task_dir in task_dirs:
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name
        chunks = chunk_directory(task_dir)
        for chunk in chunks:
            index.add_chunk(chunk)
        per_task_stats[task_id] = {
            "chunks": len(chunks),
            "files": len({c.file_path for c in chunks}),
        }

    # Save chunks
    chunks_path = out_dir / "code_chunks.jsonl"
    index.save_chunks(chunks_path)

    # Build graphs and stats
    stats = index.to_dict()
    stats["per_task"] = per_task_stats
    stats["chunks_path"] = str(chunks_path)

    stats_path = out_dir / "index_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"# Code RAG Index Built")
    print(f"  total_chunks: {index.total_chunks}")
    print(f"  unique_files: {index.unique_files}")
    print(f"  unique_terms: {index.unique_terms}")
    print(f"  tasks_indexed: {len(per_task_stats)}")
    print(f"  output: {chunks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
