from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.baselines.aider_runner import run_aider_baseline
from codeguide_agent.eval.run_eval import DEFAULT_TEMP_ROOT, discover_tasks, pytest_available, pytest_required, DEV_INSTALL_MESSAGE
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import make_policy


DEFAULT_REPORT = Path("data/mini_repo_debug/reports/eval_compare.json")


def compare_policies(
    root: str | Path,
    policies: list[str],
    limit: int | None = None,
    report_path: str | Path = DEFAULT_REPORT,
    temp_root: str | Path = DEFAULT_TEMP_ROOT,
    trajectories_dir: str | Path = "data/mini_repo_debug/trajectories",
) -> dict[str, Any]:
    tasks = discover_tasks(root)
    if limit is not None:
        tasks = tasks[:limit]
    collector = RolloutCollector(trajectories_dir=trajectories_dir)
    report: dict[str, Any] = {
        "root": str(root),
        "policies": policies,
        "gold_is_pipeline_validation_only": "gold" in policies,
        "results": {},
        "summary": {},
    }
    for policy_name in policies:
        if policy_name == "aider":
            aider_report = run_aider_baseline(
                root=root,
                limit=limit,
                output=Path(report_path).parent / "aider_baseline_report.json",
                temp_root=Path(temp_root) / policy_name,
            )
            results = aider_report["results"]
            report["results"][policy_name] = results
            report["summary"][policy_name] = summarize_policy(results)
            report["summary"][policy_name]["available"] = aider_report["summary"]["available"]
            report["summary"][policy_name]["availability"] = aider_report["summary"]["availability"]
            report["summary"][policy_name]["skip_reason"] = aider_report["summary"]["skip_reason"]
            report["summary"][policy_name]["aider_report_path"] = aider_report["report_path"]
            continue
        results = []
        for task in tasks:
            result = collector.collect(
                task=task,
                policy=make_policy(policy_name),
                temp_root=Path(temp_root) / policy_name,
                max_steps=8,
                run_hidden=policy_name == "gold",
            )
            results.append(result)
        report["results"][policy_name] = results
        report["summary"][policy_name] = summarize_policy(results)

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report["report_path"] = str(output)
    return report


def summarize_policy(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    if count == 0:
        return {
            "num_tasks": 0,
            "availability": "available",
            "skipped_count": 0,
            "success_rate": 0.0,
            "public_pass_rate": 0.0,
            "hidden_pass_rate": 0.0,
            "gold_file_hit_at_3_rate": 0.0,
            "gold_function_hit_at_3_rate": 0.0,
            "gold_file_patched_rate": 0.0,
            "gold_function_patched_rate": 0.0,
            "leakage_rate": 0.0,
            "forbidden_file_access_rate": 0.0,
            "oracle_metadata_leakage_rate": 0.0,
            "gold_identifier_visible_rate": 0.0,
            "original_repo_unchanged_rate": 0.0,
            "average_steps": 0.0,
            "average_tool_calls": 0.0,
            "average_llm_calls": 0.0,
            "invalid_action_rate": 0.0,
            "skip_reason": "",
        }

    def rate_reward(key: str) -> float:
        return round(sum(1 for result in results if result.get("reward", {}).get(key)) / count, 4)

    def rate_result_or_reward(result_key: str, reward_key: str | None = None) -> float:
        reward_key = reward_key or result_key
        return round(
            sum(1 for result in results if result.get(result_key) or result.get("reward", {}).get(reward_key)) / count,
            4,
        )

    skipped_count = sum(1 for result in results if result.get("status") == "skipped")
    availability = _availability(results, skipped_count)
    return {
        "num_tasks": count,
        "availability": availability,
        "skip_reason": _skip_reason(results),
        "skipped_count": skipped_count,
        "success_rate": round(
            sum(1 for result in results if result.get("success") or result.get("status") == "success") / count,
            4,
        ),
        "public_pass_rate": rate_result_or_reward("public_test_pass", "public_pass"),
        "hidden_pass_rate": rate_result_or_reward("hidden_test_pass", "hidden_pass"),
        "gold_file_hit_at_3_rate": rate_reward("gold_file_hit_at_3"),
        "gold_function_hit_at_3_rate": rate_reward("gold_function_hit_at_3"),
        "gold_file_patched_rate": rate_result_or_reward("gold_file_patched"),
        "gold_function_patched_rate": rate_result_or_reward("gold_function_patched"),
        "leakage_rate": rate_result_or_reward("leakage_detected"),
        "forbidden_file_access_rate": rate_result_or_reward("forbidden_file_access"),
        "oracle_metadata_leakage_rate": rate_result_or_reward("oracle_metadata_leakage"),
        "gold_identifier_visible_rate": rate_result_or_reward("gold_identifier_visible"),
        "original_repo_unchanged_rate": round(sum(1 for result in results if result.get("original_repo_unchanged")) / count, 4),
        "average_steps": round(sum(float(result.get("steps", 0)) for result in results) / count, 4),
        "average_tool_calls": round(
            sum(float(result.get("tool_calls", result.get("steps", 0))) for result in results) / count,
            4,
        ),
        "average_llm_calls": round(sum(float(result.get("llm_calls", 0)) for result in results) / count, 4),
        "invalid_action_rate": round(sum(1 for result in results if result.get("invalid_action_count", 0) > 0) / count, 4),
    }


def print_table(report: dict[str, Any]) -> None:
    headers = [
        "policy",
        "availability",
        "success_rate",
        "public_pass_rate",
        "hidden_pass_rate",
        "gold_file_hit_at_3_rate",
        "gold_function_hit_at_3_rate",
        "gold_file_patched_rate",
        "leakage_rate",
        "forbidden_file_access_rate",
        "oracle_metadata_leakage_rate",
        "gold_identifier_visible_rate",
        "original_repo_unchanged_rate",
        "average_steps",
        "average_llm_calls",
        "invalid_action_rate",
        "skip_reason",
    ]
    print("\t".join(headers))
    for policy in report["policies"]:
        summary = report["summary"][policy]
        label = f"{policy}*" if policy == "gold" else policy
        print("\t".join(str(summary.get(header, label if header == "policy" else "")) for header in headers))
    if "gold" in report["policies"]:
        print("* gold is pipeline validation only, not real policy performance")
    print(f"report_path: {report['report_path']}")


def _availability(results: list[dict[str, Any]], skipped_count: int) -> str:
    labels = {str(result.get("availability", "")) for result in results if result.get("availability")}
    if "mock" in labels:
        return "mock"
    if "skipped" in labels or skipped_count == len(results):
        return "skipped"
    return "available"


def _skip_reason(results: list[dict[str, Any]]) -> str:
    reasons = [str(result.get("skip_reason", "")) for result in results if result.get("skip_reason")]
    return reasons[0] if reasons else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Mini-Repo-Debug rollout policies.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--policies", default="noop,scripted,heuristic,gold")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--temp-root", default=str(DEFAULT_TEMP_ROOT))
    parser.add_argument("--trajectories-dir", default="data/mini_repo_debug/trajectories")
    args = parser.parse_args()

    policies = [policy.strip() for policy in args.policies.split(",") if policy.strip()]
    tasks = discover_tasks(args.root)
    if args.limit is not None:
        tasks = tasks[: args.limit]
    if pytest_required(tasks, run_hidden=("gold" in policies or "aider" in policies)) and not pytest_available():
        print(DEV_INSTALL_MESSAGE)
        return 2

    report = compare_policies(args.root, policies, args.limit, args.report, args.temp_root, args.trajectories_dir)
    print_table(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
