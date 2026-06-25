#!/usr/bin/env python3
"""History RAG offline ablation — quality vs strict safety modes.

Usage:
    python scripts/run_history_rag_ablation.py \\
      --root data/mini_repo_debug \\
      --index data/mini_repo_debug/history_index/experience_records.jsonl \\
      --out data/mini_repo_debug/history_index/ablation_results.json
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

from codeguide_agent.rag.history_index import HistoryIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="History RAG ablation study")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--index", default="data/mini_repo_debug/history_index/experience_records.jsonl")
    parser.add_argument("--out", default="data/mini_repo_debug/history_index/ablation_results.json")
    args = parser.parse_args()

    root = Path(args.root)
    index_path = Path(args.index)
    out_path = Path(args.out)

    if not index_path.exists():
        print(f"ERROR: index not found: {index_path}")
        return 1

    index = HistoryIndex.load(index_path)

    results = run_ablation(index)
    results["index_path"] = str(index_path)
    results["total_records"] = len(index.records)
    results["unique_tasks"] = len(index.task_ids)
    results["unique_families"] = len(index.generator_families)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Print summary
    print("# History RAG Ablation Results")
    print(f"  index: {len(index.records)} records, {len(index.task_ids)} tasks, {len(index.generator_families)} families")
    for mode in ["quality", "strict", "strict_full"]:
        m = results["modes"].get(mode, {})
        print(f"\n  [{mode.upper()} MODE]")
        print(f"    leakage_safe: {m.get('leakage_safe', 'N/A')}")
        for k in ["family_hit_at_1", "family_hit_at_3", "family_hit_at_5",
                   "file_hit_at_1", "file_hit_at_3", "file_hit_at_5"]:
            print(f"    {k}: {m.get(k, 'N/A'):.4f}" if isinstance(m.get(k), float) else f"    {k}: {m.get(k, 'N/A')}")
        print(f"    avg_top5: {m.get('avg_top5', 'N/A')}")
        print(f"    total_queries: {m.get('total_queries', 'N/A')}")
        print(f"    coverage_empty_count: {m.get('coverage_empty_count', 'N/A')}")
        print(f"    coverage_empty_pct: {m.get('coverage_empty_pct', 'N/A')}")

    print(f"\n  overall_passed: {results.get('overall_passed', False)}")
    return 0 if results.get("overall_passed", False) else 1


def run_ablation(index: HistoryIndex) -> dict[str, Any]:
    results: dict[str, Any] = {
        "modes": {},
        "overall_passed": True,
    }

    # Collect all SFT gold-reference records (one per task) as query targets
    gold_records = [r for r in index.records if r.experience_id.endswith("_gold_reference")]

    modes_to_run = ["quality", "strict", "strict_full"]
    for mode in modes_to_run:
        mode_results = _run_mode(index, gold_records, mode)
        results["modes"][mode] = mode_results
        # Only quality mode is required to pass; strict_full is expected empty
        # in single-split datasets and is informational.
        if mode == "quality" and not mode_results.get("passed", False):
            results["overall_passed"] = False
        if mode == "strict" and not mode_results.get("leakage_safe", True):
            results["overall_passed"] = False

    # Leakage check across all retrieval views
    leakage = _check_ablation_leakage(index)
    results["leakage"] = leakage
    if not leakage.get("passed", False):
        results["overall_passed"] = False

    return results


def _run_mode(
    index: HistoryIndex,
    gold_records: list,
    mode: str,
) -> dict[str, Any]:
    """Run ablation for one mode across all gold records.

    Modes:
      - quality:    exclude task_id + patch_hash only (maximize recall)
      - strict:     exclude task_id + family + patch_hash + pattern_hash (4-dim, no split isolation)
      - strict_full: exclude all 5 dimensions including split (requires multi-split data)
    """
    # Per-query metrics
    family_hit_at_1 = 0
    family_hit_at_3 = 0
    family_hit_at_5 = 0
    file_hit_at_1 = 0
    file_hit_at_3 = 0
    file_hit_at_5 = 0
    family_queries = 0
    file_queries = 0
    top_k_counts: list[int] = []
    coverage_empty = 0
    total = 0
    leakage_safe = True
    leakage_violations: list[str] = []

    for gold in gold_records:
        query = gold.retrieval_view.get("issue_summary", "")
        if not query:
            continue
        total += 1

        gold_family = gold.generator_family
        gold_files = set(gold.retrieval_view.get("changed_files", []))

        # Single top-5 retrieval — extract all hit@k from this one result
        retrieved = _retrieve_for_mode(index, gold, mode, top_k=5)
        top_k_counts.append(len(retrieved))

        # Leakage check
        for r in retrieved:
            rv_str = json.dumps(r.retrieval_view).lower()
            if "diff --git" in rv_str:
                leakage_safe = False
                leakage_violations.append(f"{r.experience_id}: full diff in retrieval_view")
            if "hidden_test" in rv_str or "tests_hidden" in rv_str:
                leakage_safe = False
                leakage_violations.append(f"{r.experience_id}: hidden test in retrieval_view")

        # Family hit@k — extract from single retrieval (monotonic guarantee)
        if gold_family:
            family_queries += 1
            families_at_1 = {r.generator_family for r in retrieved[:1]}
            families_at_3 = {r.generator_family for r in retrieved[:3]}
            families_at_5 = {r.generator_family for r in retrieved[:5]}
            if gold_family in families_at_1:
                family_hit_at_1 += 1
            if gold_family in families_at_3:
                family_hit_at_3 += 1
            if gold_family in families_at_5:
                family_hit_at_5 += 1

        # File hit@k — extract from single retrieval
        if gold_files:
            file_queries += 1
            files_at_1: set[str] = set()
            for r in retrieved[:1]:
                files_at_1.update(r.retrieval_view.get("changed_files", []))
            files_at_3: set[str] = set()
            for r in retrieved[:3]:
                files_at_3.update(r.retrieval_view.get("changed_files", []))
            files_at_5: set[str] = set()
            for r in retrieved[:5]:
                files_at_5.update(r.retrieval_view.get("changed_files", []))
            if gold_files & files_at_1:
                file_hit_at_1 += 1
            if gold_files & files_at_3:
                file_hit_at_3 += 1
            if gold_files & files_at_5:
                file_hit_at_5 += 1

        if len(retrieved) == 0:
            coverage_empty += 1

    avg_top5 = sum(top_k_counts) / max(1, total) if top_k_counts else 0.0

    return {
        "mode": mode,
        "family_hit_at_1": round(family_hit_at_1 / max(1, family_queries), 4),
        "family_hit_at_3": round(family_hit_at_3 / max(1, family_queries), 4),
        "family_hit_at_5": round(family_hit_at_5 / max(1, family_queries), 4),
        "file_hit_at_1": round(file_hit_at_1 / max(1, file_queries), 4),
        "file_hit_at_3": round(file_hit_at_3 / max(1, file_queries), 4),
        "file_hit_at_5": round(file_hit_at_5 / max(1, file_queries), 4),
        "avg_top5": round(avg_top5, 4),
        "total_queries": total,
        "family_queries": family_queries,
        "file_queries": file_queries,
        "coverage_empty_count": coverage_empty,
        "coverage_empty_pct": round(coverage_empty / max(1, total) * 100, 2),
        "leakage_safe": leakage_safe,
        "leakage_violations": leakage_violations,
        "passed": leakage_safe and coverage_empty < total,
    }


def _retrieve_for_mode(index: HistoryIndex, gold, mode: str, top_k: int = 5):
    """Single retrieval dispatch for a given mode to avoid duplication."""
    query = gold.retrieval_view.get("issue_summary", "")
    if mode == "quality":
        return index.retrieve_quality(
            query=query, top_k=top_k,
            exclude_task_ids={gold.task_id},
            exclude_patch_hashes={gold.patch_hash},
        )
    elif mode == "strict":
        return index.retrieve_strict(
            query=query, top_k=top_k,
            exclude_task_ids={gold.task_id},
            exclude_generator_families={gold.generator_family} if gold.generator_family else set(),
            exclude_patch_hashes={gold.patch_hash},
            exclude_issue_pattern_hashes={gold.issue_pattern_hash} if gold.issue_pattern_hash else set(),
        )
    elif mode == "strict_full":
        return index.retrieve_strict(
            query=query, top_k=top_k,
            exclude_task_ids={gold.task_id},
            exclude_generator_families={gold.generator_family} if gold.generator_family else set(),
            exclude_patch_hashes={gold.patch_hash},
            exclude_issue_pattern_hashes={gold.issue_pattern_hash} if gold.issue_pattern_hash else set(),
            exclude_splits={gold.split} if gold.split else set(),
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")


def _check_ablation_leakage(index: HistoryIndex) -> dict[str, Any]:
    """Global leakage check across all retrieval views in the index."""
    violations = []
    forbidden_in_retrieval = ["diff --git", "gold.patch", "hidden_test", "tests_hidden", "oracle"]
    for rec in index.records:
        rv = json.dumps(rec.retrieval_view).lower()
        for term in forbidden_in_retrieval:
            if term.replace("_", "") in rv.replace("_", ""):
                violations.append(f"{rec.experience_id}: '{term}' in retrieval_view")
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "total_checked": len(index.records),
    }


if __name__ == "__main__":
    raise SystemExit(main())
