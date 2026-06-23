#!/usr/bin/env python3
"""Offline evaluation of History RAG retrieval quality and leakage safety.

Usage:
    python scripts/eval_history_rag_retrieval.py \\
      --root data/mini_repo_debug \\
      --index data/mini_repo_debug/history_index/experience_records.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.rag.history_index import HistoryIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval History RAG retrieval")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--index", default="data/mini_repo_debug/history_index/experience_records.jsonl")
    args = parser.parse_args()

    root = Path(args.root)
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Index not found: {index_path}")
        return 1

    index = HistoryIndex.load(index_path)
    results = run_evals(index)
    results["index_path"] = str(index_path)
    results["index_size"] = len(index.records)

    out_path = Path(args.root) / "history_index" / "eval_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(results, indent=2))
    return 0 if results["overall_passed"] else 1


def run_evals(index: HistoryIndex) -> dict:
    results = {"tests": [], "overall_passed": True}

    # Test 1: basic retrieval by query
    if index.records:
        rec = index.records[0]
        query = rec.retrieval_view.get("issue_summary", "")
        retrieved = index.retrieve(query=query, top_k=3)
        test1 = {
            "name": "basic_retrieval",
            "passed": len(retrieved) > 0,
            "top_k_returned": len(retrieved),
        }
        results["tests"].append(test1)

    # Test 2: exclude by task_id
    if len(index.records) >= 2:
        rec = index.records[0]
        retrieved = index.retrieve(
            query=rec.retrieval_view.get("issue_summary", ""),
            top_k=10,
            exclude_task_ids={rec.task_id},
        )
        task_ids = {r.task_id for r in retrieved}
        test2 = {
            "name": "exclude_task_id",
            "passed": rec.task_id not in task_ids,
            "excluded_id": rec.task_id,
            "found_ids": sorted(task_ids),
        }
        results["tests"].append(test2)

    # Test 3: exclude by generator_family
    families = {rec.generator_family for rec in index.records if rec.generator_family}
    if families:
        fam = next(iter(families))
        retrieved = index.retrieve(query="", top_k=50, exclude_generator_families={fam})
        found_families = {r.generator_family for r in retrieved}
        test3 = {
            "name": "exclude_generator_family",
            "passed": fam not in found_families,
            "excluded_family": fam,
            "found_families": sorted(found_families),
        }
        results["tests"].append(test3)

    # Test 4: exclude by patch_hash
    hashes = {rec.patch_hash for rec in index.records if rec.patch_hash}
    if hashes:
        ph = next(iter(hashes))
        retrieved = index.retrieve(query="", top_k=50, exclude_patch_hashes={ph})
        found_hashes = {r.patch_hash for r in retrieved}
        test4 = {
            "name": "exclude_patch_hash",
            "passed": ph not in found_hashes,
        }
        results["tests"].append(test4)

    # Test 5: retrieval view does not leak full diff
    leakage_free = True
    leaked = []
    for rec in index.records:
        rv_str = json.dumps(rec.retrieval_view).lower()
        if "diff --git" in rv_str:
            leakage_free = False
            leaked.append(rec.experience_id)
    test5 = {
        "name": "no_full_diff_in_retrieval_view",
        "passed": leakage_free,
        "leaked_experience_ids": leaked,
    }
    results["tests"].append(test5)

    # Test 6: retrieval view does not leak hidden tests
    hidden_leak_free = True
    hidden_leaked = []
    for rec in index.records:
        rv_str = json.dumps(rec.retrieval_view).lower()
        if "hidden_test" in rv_str or "tests_hidden" in rv_str:
            hidden_leak_free = False
            hidden_leaked.append(rec.experience_id)
    test6 = {
        "name": "no_hidden_test_in_retrieval_view",
        "passed": hidden_leak_free,
        "leaked_experience_ids": hidden_leaked,
    }
    results["tests"].append(test6)

    # Test 7: visibility flag respected
    for rec in index.records:
        if not rec.visibility.get("allow_full_diff_in_retrieval_prompt", False):
            rv_str = json.dumps(rec.retrieval_view).lower()
            if "gold_patch" in rv_str:
                results["tests"].append({"name": "visibility_flag_respected", "passed": False, "violator": rec.experience_id})
                break
    else:
        results["tests"].append({"name": "visibility_flag_respected", "passed": True})

    results["overall_passed"] = all(t["passed"] for t in results["tests"])
    return results


if __name__ == "__main__":
    raise SystemExit(main())
