#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


BUG_TYPE_HINTS = {
    "parsing_edge_case": "Public covers simple parsing; hidden covers malformed separators, whitespace, or empty fields.",
    "path_handling": "Public covers a simple relative path; hidden covers nested, absolute, or parent paths.",
    "cache_key": "Public covers one input; hidden covers collision, normalization, or parameter-sensitive keys.",
    "optional_default_args": "Public covers omitted argument; hidden covers explicit mutable argument aliasing.",
    "boundary_condition": "Public covers normal range; hidden covers empty, first, last, or out-of-range behavior.",
    "string_normalization": "Public covers lowercase input; hidden covers whitespace, case, unicode, or punctuation.",
    "dict_mutation": "Public covers returned value; hidden checks caller object is not unexpectedly mutated.",
    "date_boundary": "Public covers normal date; hidden covers same-day, timezone, leap day, or boundary comparison.",
    "json_config_parsing": "Public covers valid JSON; hidden covers blank lines, comments, missing fields, or bad types.",
    "cli_argument_propagation": "Public covers direct function call; hidden covers CLI argument propagation.",
    "error_handling": "Public covers found case; hidden covers missing case and exception semantics.",
    "numeric_edge_case": "Public covers positive numbers; hidden covers zero, negative, empty, or precision behavior.",
    "sorting_filtering": "Public covers basic sort; hidden covers tie-breaking, stability, duplicates, or filters.",
    "service_helper_integration": "Public covers helper only; hidden covers integration between helper and service wrapper.",
    "case_insensitive_handling": "Public covers exact case; hidden covers mixed case and normalization.",
    "multi_file_integration": "Public covers one function; hidden covers cross-file call chain.",
    "stateful_side_effect": "Public covers first call; hidden covers repeated calls or state isolation.",
    "idempotency": "Public covers single execution; hidden covers repeated execution producing same result.",
    "validation_logic": "Public covers valid input; hidden covers invalid input and error message semantics.",
    "config_merge": "Public covers shallow config; hidden covers nested config, override order, or copy semantics.",
}


def load_backlog(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_issue(record: dict) -> str:
    task_id = record["task_id"]
    bug_type = record["bug_type"]
    hint = BUG_TYPE_HINTS.get(bug_type, "Define a public-hidden generalization gap.")
    return f"""# {task_id}: {bug_type}

## Problem

TODO: Describe the user-visible bug without revealing hidden tests or the exact gold patch.

## Expected behavior

TODO: Describe the intended behavior at a product/spec level.

## Public-hidden generalization axis

{hint}

## Constraints

- Keep the task offline and deterministic.
- Do not mention hidden test names.
- Do not reveal metadata paths or gold patch paths.
- Keep the gold patch minimal and realistic.
"""


def render_metadata(record: dict) -> str:
    metadata = {
        "task_id": record["task_id"],
        "bug_type": record["bug_type"],
        "difficulty": record["difficulty"],
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "target_files": record.get("target_files", []),
        "target_functions": record.get("target_functions", []),
        "expected_failure_mode": record.get("expected_failure_mode", "to_be_defined"),
        "generalization_axis": record.get("generalization_axis", "to_be_defined"),
        "oracle_leakage_risk": "low_if_issue_and_public_tests_do_not_reveal_hidden_cases",
        "status": "planned_skeleton",
    }
    return json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"


def render_public_test(record: dict) -> str:
    return f"""def test_public_placeholder():
    # TODO: Replace with meaningful public tests for {record["task_id"]}.
    assert True
"""


def render_hidden_test(record: dict) -> str:
    return f"""def test_hidden_placeholder():
    # TODO: Replace with hidden generalization tests for {record["task_id"]}.
    assert True
"""


def render_source(record: dict) -> str:
    return f"""from __future__ import annotations


def placeholder():
    # TODO: Replace with buggy implementation for {record["task_id"]}.
    return None
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backlog", default="data/mini_repo_debug/task_backlog.json")
    parser.add_argument("--out", default="data/mini_repo_debug/planned_task_skeletons")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    backlog = load_backlog(Path(args.backlog))[: args.limit]
    out = Path(args.out)

    for record in backlog:
        task_dir = out / record["task_id"]
        write(task_dir / "issue.md", render_issue(record))
        write(task_dir / "metadata.json", render_metadata(record))
        write(task_dir / "src" / "placeholder.py", render_source(record))
        write(task_dir / "tests" / "test_public_placeholder.py", render_public_test(record))
        write(task_dir / "tests_hidden" / "test_hidden_placeholder.py", render_hidden_test(record))
        write(task_dir / "gold.patch", "TODO: replace with real unified diff.\n")

    summary = {
        "output_dir": str(out),
        "skeleton_count": len(backlog),
        "first_task": backlog[0]["task_id"] if backlog else None,
        "last_task": backlog[-1]["task_id"] if backlog else None,
        "active_dataset": False,
        "note": "Skeletons are planning artifacts and must not be treated as active benchmark tasks.",
    }
    write(out / "skeleton_summary.json", json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
