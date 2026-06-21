#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT / "data" / "mini_repo_debug" / "repos"
TASK_IDS = [f"task_{index:03d}" for index in range(31, 41)]


TASKS: dict[str, dict] = {
    "task_031": {
        "bug_type": "error_handling",
        "package": "task_031_lib",
        "files": {
            "task_031_lib/ports.py": (
                '''from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_port(config: dict) -> int:
    return int(config.get("port", 8080))
''',
                '''from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_port(config: dict) -> int:
    try:
        port = int(config.get("port", 8080))
    except (TypeError, ValueError) as exc:
        raise ConfigError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ConfigError("port out of range")
    return port
''',
            )
        },
        "target_functions": ["parse_port"],
        "issue": """# Validate configured network ports

`parse_port` should accept a missing port by using the default, but invalid ports should raise `ConfigError` instead of leaking raw exceptions or accepting impossible values.
""",
        "public_test": '''from task_031_lib.ports import parse_port


def test_default_port():
    assert parse_port({}) == 8080


def test_string_port():
    assert parse_port({"port": "9000"}) == 9000
''',
        "hidden_test": '''from task_031_lib.ports import ConfigError, parse_port


def test_non_numeric_port_raises_config_error():
    try:
        parse_port({"port": "soon"})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")


def test_out_of_range_port_raises_config_error():
    try:
        parse_port({"port": 70000})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Valid defaults work, but invalid ports leak raw exceptions or pass through.",
        "generalization_axis": "Public covers valid parsing; hidden covers validation failures.",
    },
    "task_032": {
        "bug_type": "numeric_edge_case",
        "package": "task_032_lib",
        "files": {
            "task_032_lib/percent.py": (
                '''from __future__ import annotations


def percent_change(old: float, new: float) -> float:
    return (new - old) / new * 100
''',
                '''from __future__ import annotations


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("old value must be non-zero")
    return (new - old) / old * 100
''',
            )
        },
        "target_functions": ["percent_change"],
        "issue": """# Percent change uses the wrong denominator

`percent_change(old, new)` should report change relative to the old value. It currently divides by the new value, producing incorrect metrics.
""",
        "public_test": '''from task_032_lib.percent import percent_change


def test_percent_increase():
    assert percent_change(100, 125) == 25


def test_percent_decrease():
    assert percent_change(200, 150) == -25
''',
        "hidden_test": '''from task_032_lib.percent import percent_change


def test_zero_old_value_raises():
    try:
        percent_change(0, 5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The formula divides by the new value and does not guard a zero baseline.",
        "generalization_axis": "Public covers formula correctness; hidden covers zero baseline handling.",
    },
    "task_033": {
        "bug_type": "sorting_filtering",
        "package": "task_033_lib",
        "files": {
            "task_033_lib/catalog.py": (
                '''from __future__ import annotations


def visible_titles(items: list[dict], category: str) -> list[str]:
    visible = [item for item in items if item.get("visible") and item.get("category") == category]
    return [item["title"] for item in sorted(visible, key=lambda item: item["title"])]
''',
                '''from __future__ import annotations


def visible_titles(items: list[dict], category: str) -> list[str]:
    visible = [item for item in items if item.get("visible") and item.get("category") == category]
    ranked = sorted(visible, key=lambda item: (-item.get("priority", 0), item["title"]))
    return [item["title"] for item in ranked]
''',
            )
        },
        "target_functions": ["visible_titles"],
        "issue": """# Catalog titles should sort by priority

Visible catalog titles should be filtered by category, then sorted by descending priority with title as a tie-breaker. The current implementation only sorts alphabetically.
""",
        "public_test": '''from task_033_lib.catalog import visible_titles


def test_filters_visibility_and_category():
    items = [
        {"title": "Alpha", "category": "book", "visible": True, "priority": 1},
        {"title": "Beta", "category": "book", "visible": False, "priority": 99},
        {"title": "Gamma", "category": "game", "visible": True, "priority": 99},
    ]
    assert visible_titles(items, "book") == ["Alpha"]
''',
        "hidden_test": '''from task_033_lib.catalog import visible_titles


def test_sorts_by_priority_descending():
    items = [
        {"title": "Alpha", "category": "book", "visible": True, "priority": 1},
        {"title": "Beta", "category": "book", "visible": True, "priority": 4},
        {"title": "Aardvark", "category": "book", "visible": True, "priority": 4},
    ]
    assert visible_titles(items, "book") == ["Aardvark", "Beta", "Alpha"]
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Filtering works, but ranking ignores priority.",
        "generalization_axis": "Public covers filtering; hidden covers the sort key.",
    },
    "task_034": {
        "bug_type": "service_helper_integration",
        "package": "task_034_lib",
        "files": {
            "task_034_lib/discounts.py": (
                '''from __future__ import annotations


def apply_discount(amount: int, percent: int) -> int:
    return amount - (amount * percent // 100)
''',
                '''from __future__ import annotations


def apply_discount(amount: int, percent: int) -> int:
    return amount - round(amount * percent / 100)
''',
            ),
            "task_034_lib/orders.py": (
                '''from __future__ import annotations

from .discounts import apply_discount


def order_total(items: list[dict], discount_percent: int = 0) -> int:
    subtotal = sum(item["price"] * item.get("quantity", 1) for item in items)
    return subtotal
''',
                '''from __future__ import annotations

from .discounts import apply_discount


def order_total(items: list[dict], discount_percent: int = 0) -> int:
    subtotal = sum(item["price"] * item.get("quantity", 1) for item in items)
    return apply_discount(subtotal, discount_percent)
''',
            ),
        },
        "target_functions": ["order_total", "apply_discount"],
        "issue": """# Order totals ignore the discount helper

The order service imports `apply_discount`, but totals currently ignore discounts. The helper should also round fractional discounts consistently.
""",
        "public_test": '''from task_034_lib.orders import order_total


def test_order_total_applies_discount():
    assert order_total([{"price": 100}], discount_percent=10) == 90


def test_quantity_still_counts():
    assert order_total([{"price": 10, "quantity": 3}], discount_percent=0) == 30
''',
        "hidden_test": '''from task_034_lib.discounts import apply_discount
from task_034_lib.orders import order_total


def test_discount_rounds_fractional_amounts():
    assert apply_discount(99, 5) == 94


def test_order_total_uses_rounded_discount():
    assert order_total([{"price": 99}], discount_percent=5) == 94
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The service ignores the helper and the helper floors fractional discounts.",
        "generalization_axis": "Public covers integration; hidden covers helper rounding.",
    },
    "task_035": {
        "bug_type": "case_insensitive_handling",
        "package": "task_035_lib",
        "files": {
            "task_035_lib/roles.py": (
                '''from __future__ import annotations


def has_role(user_roles: list[str], required: str) -> bool:
    return required in user_roles
''',
                '''from __future__ import annotations


def has_role(user_roles: list[str], required: str) -> bool:
    wanted = required.strip().casefold()
    return any(role.strip().casefold() == wanted for role in user_roles)
''',
            )
        },
        "target_functions": ["has_role"],
        "issue": """# Role checks should ignore case and surrounding spaces

Role names come from multiple systems. `has_role` should match roles case-insensitively and ignore accidental whitespace.
""",
        "public_test": '''from task_035_lib.roles import has_role


def test_exact_role_match():
    assert has_role(["admin", "viewer"], "admin") is True


def test_missing_role():
    assert has_role(["viewer"], "admin") is False
''',
        "hidden_test": '''from task_035_lib.roles import has_role


def test_case_insensitive_match():
    assert has_role(["Admin"], "admin") is True


def test_whitespace_is_ignored():
    assert has_role([" viewer "], "viewer") is True
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Exact matches work, but case and whitespace variants fail.",
        "generalization_axis": "Public covers exact membership; hidden covers normalization.",
    },
    "task_036": {
        "bug_type": "multi_file_integration",
        "package": "task_036_lib",
        "files": {
            "task_036_lib/formatters.py": (
                '''from __future__ import annotations


def format_currency(cents: int) -> str:
    return f"${cents / 100:.2f}"
''',
                '''from __future__ import annotations


def format_currency(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"
''',
            ),
            "task_036_lib/receipt.py": (
                '''from __future__ import annotations

from .formatters import format_currency


def render_receipt(total_cents: int) -> str:
    return f"Total: {total_cents}"
''',
                '''from __future__ import annotations

from .formatters import format_currency


def render_receipt(total_cents: int) -> str:
    return f"Total: {format_currency(total_cents)}"
''',
            ),
        },
        "target_functions": ["render_receipt", "format_currency"],
        "issue": """# Receipts should use the shared currency formatter

Receipt rendering currently prints raw cents instead of the shared currency format. The formatter also needs to handle negative adjustments without odd placement.
""",
        "public_test": '''from task_036_lib.receipt import render_receipt


def test_receipt_formats_positive_total():
    assert render_receipt(1234) == "Total: $12.34"
''',
        "hidden_test": '''from task_036_lib.formatters import format_currency
from task_036_lib.receipt import render_receipt


def test_formatter_handles_negative_adjustment():
    assert format_currency(-50) == "-$0.50"


def test_receipt_uses_negative_format():
    assert render_receipt(-50) == "Total: -$0.50"
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "Receipt bypasses the formatter and negative formatting is inconsistent.",
        "generalization_axis": "Public covers integration; hidden covers helper behavior through both files.",
    },
    "task_037": {
        "bug_type": "stateful_side_effect",
        "package": "task_037_lib",
        "files": {
            "task_037_lib/batches.py": (
                '''from __future__ import annotations


def add_batch_item(item: str, batch: list[str] = []) -> list[str]:
    batch.append(item)
    return batch
''',
                '''from __future__ import annotations


def add_batch_item(item: str, batch: list[str] | None = None) -> list[str]:
    values = list(batch) if batch is not None else []
    values.append(item)
    return values
''',
            )
        },
        "target_functions": ["add_batch_item"],
        "issue": """# Batch helper leaks state across calls

`add_batch_item` should return a new batch with the item added. Separate calls without an explicit batch must not share state, and caller-provided lists should not be mutated.
""",
        "public_test": '''from task_037_lib.batches import add_batch_item


def test_default_batch_is_not_shared():
    assert add_batch_item("a") == ["a"]
    assert add_batch_item("b") == ["b"]
''',
        "hidden_test": '''from task_037_lib.batches import add_batch_item


def test_caller_list_is_not_mutated():
    original = ["a"]
    result = add_batch_item("b", original)
    assert result == ["a", "b"]
    assert original == ["a"]
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "A mutable default leaks state and explicit lists are mutated in place.",
        "generalization_axis": "Public covers default state leakage; hidden covers input aliasing.",
    },
    "task_038": {
        "bug_type": "idempotency",
        "package": "task_038_lib",
        "files": {
            "task_038_lib/tags.py": (
                '''from __future__ import annotations


def ensure_tag(tags: list[str], tag: str) -> list[str]:
    return tags + [tag]
''',
                '''from __future__ import annotations


def ensure_tag(tags: list[str], tag: str) -> list[str]:
    if tag in tags:
        return list(tags)
    return list(tags) + [tag]
''',
            )
        },
        "target_functions": ["ensure_tag"],
        "issue": """# Adding a tag should be idempotent

`ensure_tag` should add a missing tag while preserving existing order. Re-adding an existing tag should not duplicate it or mutate the input list.
""",
        "public_test": '''from task_038_lib.tags import ensure_tag


def test_adds_missing_tag():
    assert ensure_tag(["red"], "sale") == ["red", "sale"]


def test_does_not_mutate_input_when_adding():
    tags = ["red"]
    ensure_tag(tags, "sale")
    assert tags == ["red"]
''',
        "hidden_test": '''from task_038_lib.tags import ensure_tag


def test_existing_tag_is_not_duplicated():
    assert ensure_tag(["red", "sale"], "sale") == ["red", "sale"]
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Adding a missing tag works, but existing tags are duplicated.",
        "generalization_axis": "Public covers add behavior; hidden covers idempotency.",
    },
    "task_039": {
        "bug_type": "validation_logic",
        "package": "task_039_lib",
        "files": {
            "task_039_lib/usernames.py": (
                '''from __future__ import annotations


def is_valid_username(value: str) -> bool:
    return len(value) >= 3
''',
                '''from __future__ import annotations

import re


def is_valid_username(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,15}", value))
''',
            )
        },
        "target_functions": ["is_valid_username"],
        "issue": """# Username validation is too loose

Usernames should start with a letter, contain only letters, digits, and underscores, and be between 3 and 16 characters long.
""",
        "public_test": '''from task_039_lib.usernames import is_valid_username


def test_rejects_too_short_name():
    assert is_valid_username("ab") is False


def test_accepts_normal_name():
    assert is_valid_username("ada_1") is True
''',
        "hidden_test": '''from task_039_lib.usernames import is_valid_username


def test_rejects_digit_prefix():
    assert is_valid_username("1ada") is False


def test_rejects_symbols():
    assert is_valid_username("ada!") is False
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Length is checked, but character and prefix rules are ignored.",
        "generalization_axis": "Public covers length; hidden covers full validation syntax.",
    },
    "task_040": {
        "bug_type": "config_merge",
        "package": "task_040_lib",
        "files": {
            "task_040_lib/merge.py": (
                '''from __future__ import annotations


def merge_config(defaults: dict, override: dict) -> dict:
    result = dict(defaults)
    result.update(override)
    return result
''',
                '''from __future__ import annotations


def merge_config(defaults: dict, override: dict) -> dict:
    result = dict(defaults)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
''',
            )
        },
        "target_functions": ["merge_config"],
        "issue": """# Config overrides should merge nested dictionaries

`merge_config` should apply overrides without mutating defaults. Nested dictionaries should merge recursively so unspecified nested defaults are preserved.
""",
        "public_test": '''from task_040_lib.merge import merge_config


def test_top_level_override():
    assert merge_config({"debug": False}, {"debug": True}) == {"debug": True}


def test_keeps_unmentioned_top_level_default():
    assert merge_config({"debug": False, "retries": 3}, {"debug": True})["retries"] == 3
''',
        "hidden_test": '''from task_040_lib.merge import merge_config


def test_nested_dicts_are_merged():
    result = merge_config({"db": {"host": "localhost", "port": 5432}}, {"db": {"port": 5433}})
    assert result == {"db": {"host": "localhost", "port": 5433}}


def test_defaults_are_not_mutated():
    defaults = {"db": {"host": "localhost", "port": 5432}}
    merge_config(defaults, {"db": {"port": 5433}})
    assert defaults == {"db": {"host": "localhost", "port": 5432}}
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Top-level merge works, but nested defaults are overwritten.",
        "generalization_axis": "Public covers shallow merge; hidden covers recursive merge.",
    },
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def must_run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = run(cmd, cwd, env=env)
    if proc.returncode != 0:
        print(proc.stdout)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return proc


def write_task(task_id: str, spec: dict) -> None:
    task_dir = REPO_ROOT / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
    write(task_dir / spec["package"] / "__init__.py", "")
    for rel, (before, _) in spec["files"].items():
        write(task_dir / rel, before)
    write(task_dir / "issue.md", spec["issue"])
    write(task_dir / "tests" / f"test_{task_id}_public.py", spec["public_test"])
    write(task_dir / "tests_hidden" / f"test_{task_id}_hidden.py", spec["hidden_test"])
    write_metadata(task_dir, task_id, spec)
    regenerate_gold_patch(task_dir, spec)


def write_metadata(task_dir: Path, task_id: str, spec: dict) -> None:
    metadata = {
        "task_id": task_id,
        "bug_type": spec["bug_type"],
        "difficulty": "easy",
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "target_files": list(spec["files"].keys()),
        "target_functions": spec["target_functions"],
        "expected_failure_mode": spec["expected_failure_mode"],
        "generalization_axis": spec["generalization_axis"],
        "repo_path": str(Path("data/mini_repo_debug/repos") / task_id),
        "source": "manual_p42_expansion",
        "split": "train",
        "scenario": f"{spec['bug_type']} public-hidden generalization",
        "gold_patch": "gold.patch",
        "gold_files": list(spec["files"].keys()),
        "gold_functions": spec["target_functions"],
        "forbidden_behaviors": ["hard-code public examples", "modify tests", "ignore hidden edge cases"],
    }
    (task_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regenerate_gold_patch(task_dir: Path, spec: dict) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / task_dir.name
        shutil.copytree(task_dir, tmp)
        must_run(["git", "init", "-q"], tmp)
        must_run(["git", "config", "user.email", "codeguide@example.com"], tmp)
        must_run(["git", "config", "user.name", "CodeGuide"], tmp)
        must_run(["git", "add", "."], tmp)
        must_run(["git", "commit", "-q", "-m", "buggy"], tmp)
        for rel, (_, after) in spec["files"].items():
            write(tmp / rel, after)
        patch = must_run(["git", "diff", "--binary"], tmp).stdout
        if not patch.startswith("diff --git"):
            raise SystemExit(f"{task_dir.name}: generated patch is invalid")
        (task_dir / "gold.patch").write_text(patch, encoding="utf-8")


def check_patch_applies(task_id: str) -> None:
    task_dir = REPO_ROOT / task_id
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / task_id
        shutil.copytree(task_dir, tmp)
        proc = run(["git", "apply", "--check", "gold.patch"], tmp)
        if proc.returncode != 0:
            print(proc.stdout)
            raise SystemExit(f"{task_id}: gold.patch does not apply")


def simple_pytest(targets: list[Path], pythonpath: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pythonpath) + os.pathsep + str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "codeguide_agent.testing.simple_pytest"]
    cmd.extend(str(target) for target in targets)
    cmd.append("-q")
    return run(cmd, ROOT, env=env)


def verify_task(task_id: str, spec: dict) -> None:
    task_dir = REPO_ROOT / task_id
    public_proc = simple_pytest([task_dir / "tests"], task_dir)
    hidden_proc = simple_pytest([task_dir / "tests_hidden"], task_dir)
    expected_public, expected_hidden = spec["expected_buggy"]
    actual_public = "pass" if public_proc.returncode == 0 else "fail"
    actual_hidden = "pass" if hidden_proc.returncode == 0 else "fail"
    if (actual_public, actual_hidden) != (expected_public, expected_hidden):
        print(f"\n{task_id}: unexpected buggy test shape")
        print(f"expected public={expected_public}, hidden={expected_hidden}")
        print(f"actual   public={actual_public}, hidden={actual_hidden}")
        print("\n--- public output ---")
        print(public_proc.stdout)
        print("\n--- hidden output ---")
        print(hidden_proc.stdout)
        raise SystemExit(1)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / task_id
        shutil.copytree(task_dir, tmp)
        must_run(["git", "apply", "gold.patch"], tmp)
        gold_proc = simple_pytest([tmp / "tests", tmp / "tests_hidden"], tmp)
        if gold_proc.returncode != 0:
            print(f"\n{task_id}: gold patch failed tests")
            print(gold_proc.stdout)
            raise SystemExit(1)
    print(f"PASS {task_id}: buggy public={actual_public}, buggy hidden={actual_hidden}, gold=pass")


def main() -> None:
    for task_id in TASK_IDS:
        write_task(task_id, TASKS[task_id])
        check_patch_applies(task_id)
    for task_id in TASK_IDS:
        verify_task(task_id, TASKS[task_id])
    print("PASS: P42 task_031-task_040 repair and verification complete")


if __name__ == "__main__":
    main()
