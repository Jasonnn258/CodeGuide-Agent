#!/usr/bin/env python3
"""Build experience records index from Mini-Repo-Debug train_package data.

Usage:
    python scripts/build_history_rag_index.py \\
      --root data/mini_repo_debug \\
      --out data/mini_repo_debug/history_index
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.rag.history_index import build_experience_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build History RAG index")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/history_index")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    index = build_experience_records(root)
    output_path = out_dir / "experience_records.jsonl"
    index.save(output_path)

    # Report stats
    splits = {}
    families = {}
    for rec in index.records:
        splits[rec.split] = splits.get(rec.split, 0) + 1
        families[rec.generator_family] = families.get(rec.generator_family, 0) + 1

    # Check retrieval views for leakage
    leakage = _check_retrieval_leakage(index)

    stats = {
        "total_records": len(index.records),
        "by_split": splits,
        "by_generator_family": dict(sorted(families.items())),
        "retrieval_view_leakage_check": leakage,
        "output_path": str(output_path),
    }

    stats_path = out_dir / "index_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Built index: {len(index.records)} records -> {output_path}")
    print(f"  splits: {splits}")
    print(f"  families: {len(families)} unique")
    print(f"  leakage_safe: {leakage['passed']}")
    print(f"  has_leakage: {not leakage['passed']}")

    return 0 if leakage["passed"] else 1


def _check_retrieval_leakage(index) -> dict:
    violations = []
    forbidden_in_retrieval = ["diff --git", "gold.patch", "hidden_test", "tests_hidden", "oracle"]
    for rec in index.records:
        rv = json.dumps(rec.retrieval_view).lower()
        for term in forbidden_in_retrieval:
            if term.replace("_", "") in rv.replace("_", ""):
                violations.append(f"{rec.experience_id}: '{term}' found in retrieval_view")
    return {"passed": len(violations) == 0, "violations": violations}


if __name__ == "__main__":
    raise SystemExit(main())
