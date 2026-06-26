#!/usr/bin/env python3
"""Agent-loop ablation: baseline vs History RAG enabled on deterministic policies.

Usage:
    python scripts/run_agent_loop_ablation.py \\
      --root data/mini_repo_debug \\
      --index data/mini_repo_debug/history_index/experience_records.jsonl \\
      --out data/mini_repo_debug/history_index/agent_loop_ablation.json
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

from codeguide_agent.rag.agent_loop import (
    DEFAULT_MAX_CHARS_PER_SNIPPET,
    DEFAULT_MAX_SNIPPETS,
    HistoryRAGAgentLoop,
    HistoryRAGConfig,
)
from codeguide_agent.rag.history_index import HistoryIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-loop History RAG ablation")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--index", default="data/mini_repo_debug/history_index/experience_records.jsonl")
    parser.add_argument("--out", default="data/mini_repo_debug/history_index/agent_loop_ablation.json")
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# Agent-Loop History RAG Ablation")
    disabled = results.get("disabled", {})
    enabled = results.get("enabled", {})
    print(f"  [DISABLED (baseline)]")
    print(f"    total_tasks: {disabled.get('total_tasks', 0)}")
    print(f"    snippet_count: {disabled.get('total_snippets', 0)}")
    print(f"    leakage_safe: {disabled.get('leakage_safe', 'N/A')}")
    print(f"  [ENABLED (history RAG)]")
    print(f"    total_tasks: {enabled.get('total_tasks', 0)}")
    print(f"    snippet_count: {enabled.get('total_snippets', 0)}")
    print(f"    avg_snippets: {enabled.get('avg_snippets_per_task', 0):.2f}")
    print(f"    avg_chars_per_snippet: {enabled.get('avg_chars_per_snippet', 0):.0f}")
    print(f"    same_family_warnings: {enabled.get('same_family_warnings', 0)}")
    print(f"    leakage_safe: {enabled.get('leakage_safe', 'N/A')}")
    print(f"  overall_passed: {results.get('overall_passed', False)}")
    return 0 if results.get("overall_passed", False) else 1


def run_ablation(index: HistoryIndex) -> dict[str, Any]:
    gold_records = [r for r in index.records if r.experience_id.endswith("_gold_reference")]

    # --- disabled (baseline) ---
    loop_disabled = HistoryRAGAgentLoop(HistoryRAGConfig(enabled=False, index_path=""))
    loop_disabled._index = index  # inject loaded index

    disabled_results = _evaluate_tasks(loop_disabled, gold_records)

    # --- enabled ---
    loop_enabled = HistoryRAGAgentLoop(
        HistoryRAGConfig(
            enabled=True,
            index_path="",
            mode="quality",
            max_snippets=DEFAULT_MAX_SNIPPETS,
            max_chars_per_snippet=DEFAULT_MAX_CHARS_PER_SNIPPET,
        )
    )
    loop_enabled._index = index  # inject loaded index

    enabled_results = _evaluate_tasks(loop_enabled, gold_records)

    overall_passed = (
        disabled_results["leakage_safe"]
        and enabled_results["leakage_safe"]
        and enabled_results["total_snippets"] > 0  # must build something when enabled
        and disabled_results["total_snippets"] == 0  # must be empty when disabled
    )

    return {
        "disabled": disabled_results,
        "enabled": enabled_results,
        "overall_passed": overall_passed,
        "config": {
            "mode": "quality",
            "max_snippets": DEFAULT_MAX_SNIPPETS,
            "max_chars_per_snippet": DEFAULT_MAX_CHARS_PER_SNIPPET,
        },
    }


def _evaluate_tasks(loop: HistoryRAGAgentLoop, gold_records: list) -> dict[str, Any]:
    total_snippets = 0
    total_chars = 0
    same_family_warnings = 0
    per_task_snippets: list[int] = []
    per_task_results: list[dict[str, Any]] = []
    leakage_safe = True
    leakage_violations_all: list[str] = []

    for gold in gold_records:
        issue_text = gold.retrieval_view.get("issue_summary", "")
        if not issue_text:
            continue

        ctx = loop.build_history_context(
            task_id=gold.task_id,
            issue_text=issue_text,
            patch_hash=gold.patch_hash,
        )

        n = len(ctx.snippets)
        total_snippets += n
        per_task_snippets.append(n)
        total_chars += sum(len(s.get("retrieval_text", "")) for s in ctx.snippets)

        if ctx.same_family_warning:
            same_family_warnings += 1
        if not ctx.leakage_safe:
            leakage_safe = False
            leakage_violations_all.extend(ctx.leakage_violations)

        per_task_results.append({
            "task_id": gold.task_id,
            "snippet_count": n,
            "retrieved_ids": ctx.retrieved_ids,
            "same_family_warning": ctx.same_family_warning,
            "same_family_warning_detail": ctx.same_family_warning_detail,
            "leakage_safe": ctx.leakage_safe,
            "leakage_violations": ctx.leakage_violations,
            "total_available": ctx.total_available,
        })

    total = len(per_task_results)
    avg_snippets = total_snippets / max(1, total)
    avg_chars = total_chars / max(1, total_snippets) if total_snippets else 0

    return {
        "total_tasks": total,
        "total_snippets": total_snippets,
        "avg_snippets_per_task": round(avg_snippets, 2),
        "avg_chars_per_snippet": round(avg_chars, 1),
        "same_family_warnings": same_family_warnings,
        "leakage_safe": leakage_safe,
        "leakage_violations": leakage_violations_all,
        "safety_report": loop.get_safety_report(),
        "per_task": per_task_results,
    }


if __name__ == "__main__":
    raise SystemExit(main())
