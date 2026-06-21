from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _find_patch_in_record(record: dict[str, Any]) -> str:
    for key in ["final_patch", "final_diff", "patch", "diff"]:
        value = record.get(key)
        if isinstance(value, str) and value.startswith("diff --git"):
            return value

    for outer in ["chosen", "rejected", "assistant", "output"]:
        obj = record.get(outer)
        if isinstance(obj, dict):
            patch = _find_patch_in_record(obj)
            if patch:
                return patch

    return ""


def _gold_patch_for_task(task_id: str) -> str:
    repo = Path("data/mini_repo_debug/repos") / task_id
    for name in ["gold.patch", "gold.diff", "expected.patch", "patch.diff"]:
        path = repo / name
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if text.startswith("diff --git"):
                return text

    for path in repo.rglob("*.patch"):
        text = path.read_text(encoding="utf-8")
        if text.startswith("diff --git"):
            return text

    return ""


def _patch_for_record(record: dict[str, Any]) -> str:
    patch = _find_patch_in_record(record)
    if patch:
        return patch

    task_id = record.get("task_id")
    if isinstance(task_id, str):
        patch = _gold_patch_for_task(task_id)
        if patch:
            return patch

    raise AssertionError(f"could not find diff patch for fixture record: {task_id}")


def _task_009_rejected_patch() -> str:
    # This is intentionally NOT the gold fix.
    # It fixes the mutable default list, but still mutates explicit caller-provided tags.
    # Public passes; hidden generalization should fail.
    return """diff --git a/src/tags.py b/src/tags.py
index 78f4e99..fbaab89 100644
--- a/src/tags.py
+++ b/src/tags.py
@@ -1,7 +1,9 @@
 from __future__ import annotations
 
 
-def collect_tags(items: list[dict], tags: list[str] = []) -> list[str]:
+def collect_tags(items: list[dict], tags: list[str] | None = None) -> list[str]:
+    if tags is None:
+        tags = []
     for item in items:
         tag = item.get("tag")
         if tag and tag not in tags:
"""


def _task_009_gold_patch() -> str:
    return """diff --git a/src/tags.py b/src/tags.py
index 78f4e99..4bb7b2d 100644
--- a/src/tags.py
+++ b/src/tags.py
@@ -1,9 +1,10 @@
 from __future__ import annotations
 
 
-def collect_tags(items: list[dict], tags: list[str] = []) -> list[str]:
+def collect_tags(items: list[dict], tags: list[str] | None = None) -> list[str]:
+    result = list(tags) if tags is not None else []
     for item in items:
         tag = item.get("tag")
-        if tag and tag not in tags:
-            tags.append(tag)
-    return tags
+        if tag and tag not in result:
+            result.append(tag)
+    return result
"""


def _write_trajectory(
    path: Path,
    final_patch: str,
    reward_summary: dict[str, Any],
    *,
    include_hidden_failure_step: bool = False,
) -> None:
    if not final_patch.startswith("diff --git"):
        raise AssertionError(f"fixture final_patch is not a unified diff: {path}")

    reward = dict(reward_summary)
    reward.setdefault("public_pass", True)
    reward.setdefault("hidden_pass", True)
    reward.setdefault("public_pass_hidden_fail", False)
    reward.setdefault("hidden_failure_type", "none")
    reward.setdefault("patch_generalization_risk", "low")
    reward.setdefault("leakage_detected", False)
    reward.setdefault("syntax_error", False)
    reward.setdefault("changed_lines_count", 1)
    reward.setdefault("changed_files", ["src/fixture.py"])
    reward.setdefault("total_reward", 1.1)

    rows: list[dict[str, Any]] = [
        {
            "type": "step",
            "action_name": "repo_tree",
            "action_input": {"max_depth": 4},
            "observation": {"status": "success", "tree": "src/"},
        },
        {
            "type": "step",
            "action_name": "run_test",
            "action_input": {"command": "python -m pytest tests -q", "phase": "auto_public_after_edit"},
            "observation": {"status": "success", "exit_code": 0, "timeout": 30, "stdout": "2 passed", "stderr": ""},
        },
    ]

    if include_hidden_failure_step:
        rows.append(
            {
                "type": "step",
                "action_name": "run_test",
                "action_input": {"command": "python -m pytest tests_hidden -q", "phase": "final_hidden"},
                "observation": {
                    "status": "success",
                    "exit_code": 1,
                    "timeout": 30,
                    "stdout": "FAILED tests_hidden/test_tags_hidden.py::test_hidden_case\\nAssertionError",
                    "stderr": "",
                },
            }
        )

    rows.extend(
        [
            {
                "type": "step",
                "action_name": "git_diff",
                "action_input": {"phase": "final"},
                "observation": {
                    "status": "success",
                    "exit_code": 0,
                    "diff": final_patch,
                    "stdout": final_patch,
                    "stderr": "",
                },
            },
            {
                "type": "final",
                "final_patch": final_patch,
                "reward": reward,
            },
        ]
    )

    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def build_mini_repo_trajectory_fixture(tmp_path: Path) -> Path:
    """Build minimal LLM trajectory fixtures independent of generated trajectories."""
    out = tmp_path / "mini_repo_trajectory_fixture"
    out.mkdir(parents=True, exist_ok=True)

    package = Path("data/mini_repo_debug/train_package")
    sft_records = _read_jsonl(package / "sft_train.jsonl") + _read_jsonl(package / "sft_eval.jsonl")

    for record in sft_records:
        task_id = record["task_id"]
        patch = _patch_for_record(record)
        reward = dict(record.get("reward_summary", {}))
        reward.update(
            {
                "public_pass": True,
                "hidden_pass": True,
                "public_pass_hidden_fail": False,
                "hidden_failure_type": "none",
                "patch_generalization_risk": "low",
                "leakage_detected": False,
                "syntax_error": False,
                "changed_files": reward.get("changed_files") or ["src/fixture.py"],
                "changed_lines_count": reward.get("changed_lines_count") or 1,
            }
        )
        _write_trajectory(out / f"{task_id}_llm.jsonl", patch, reward)

    # Always create the one public-pass-hidden-fail LLM fixture needed by P5/P6/P7 tests.
    task_009_reward = {
        "public_pass": True,
        "hidden_pass": False,
        "public_pass_hidden_fail": True,
        "hidden_failure_type": "hidden_assertion_fail",
        "patch_generalization_risk": "medium",
        "leakage_detected": False,
        "syntax_error": False,
        "changed_lines_count": 4,
        "changed_files": ["src/tags.py"],
        "total_reward": 0.6,
    }
    _write_trajectory(
        out / "task_009_llm.jsonl",
        _task_009_rejected_patch(),
        task_009_reward,
        include_hidden_failure_step=True,
    )

    task_009_gold_reward = {
        "public_pass": True,
        "hidden_pass": True,
        "public_pass_hidden_fail": False,
        "hidden_failure_type": "none",
        "patch_generalization_risk": "low",
        "leakage_detected": False,
        "syntax_error": False,
        "changed_lines_count": 5,
        "changed_files": ["src/tags.py"],
        "total_reward": 1.1,
    }
    _write_trajectory(
        out / "task_009_gold.jsonl",
        _task_009_gold_patch(),
        task_009_gold_reward,
    )

    return out
