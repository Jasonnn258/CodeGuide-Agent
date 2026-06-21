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
TASK_IDS = [f"task_{index:03d}" for index in range(26, 31)]


TASKS: dict[str, dict] = {
    "task_026": {
        "bug_type": "json_config_parsing",
        "difficulty": "easy",
        "package": "task_026_lib",
        "files": {
            "task_026_lib/config.py": {
                "before": '''from __future__ import annotations

import json


def load_config(text: str) -> dict:
    """Load a JSON config string."""
    return json.loads(text)
''',
                "after": '''from __future__ import annotations

import json
import re


def load_config(text: str) -> dict:
    """Load a JSON config string with common config-file conveniences."""
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        cleaned_lines.append(line)
    cleaned = "\\n".join(cleaned_lines)
    cleaned = re.sub(r",\\s*([}\\]])", r"\\1", cleaned)
    return json.loads(cleaned)
''',
            }
        },
        "target_files": ["task_026_lib/config.py"],
        "target_functions": ["load_config"],
        "issue": """# Parse JSON config files used by operators

`load_config` is used for small JSON config snippets pasted into an admin tool.

It should keep supporting ordinary JSON, and it should also tolerate common config-file conveniences such as comment-only lines and trailing commas.

Please fix the parser without changing the public API.
""",
        "public_test": '''from task_026_lib.config import load_config


def test_loads_plain_json_object():
    assert load_config('{"enabled": true, "retries": 3}') == {"enabled": True, "retries": 3}


def test_loads_nested_plain_json():
    assert load_config('{"service": {"name": "api"}}')["service"]["name"] == "api"
''',
        "hidden_test": '''from task_026_lib.config import load_config


def test_ignores_comment_lines():
    text = """// deployed by ops
{
  "enabled": true
}
"""
    assert load_config(text)["enabled"] is True


def test_allows_trailing_commas():
    assert load_config('{"hosts": ["a", "b",],}') == {"hosts": ["a", "b"]}
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Plain JSON works, but config snippets with comments or trailing commas fail.",
        "generalization_axis": "Public covers strict JSON; hidden covers operator-friendly config syntax.",
    },
    "task_027": {
        "bug_type": "cli_argument_propagation",
        "difficulty": "easy",
        "package": "task_027_lib",
        "files": {
            "task_027_lib/cli.py": {
                "before": '''from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--uppercase", action="store_true")
    parser.add_argument("name")
    return parser


def render(name: str, limit: int = 10, uppercase: bool = False) -> str:
    value = name.upper() if uppercase else name
    return f"{value}:{limit}"


def main(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    return render(args.name)
''',
                "after": '''from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--uppercase", action="store_true")
    parser.add_argument("name")
    return parser


def render(name: str, limit: int = 10, uppercase: bool = False) -> str:
    value = name.upper() if uppercase else name
    return f"{value}:{limit}"


def main(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    return render(args.name, limit=args.limit, uppercase=args.uppercase)
''',
            }
        },
        "target_files": ["task_027_lib/cli.py"],
        "target_functions": ["main"],
        "issue": """# CLI flags are parsed but ignored

The small CLI helper parses `--limit` and `--uppercase`, but callers report that those options do not affect the rendered output.

Please propagate parsed arguments into the rendering layer while preserving the public function names.
""",
        "public_test": '''from task_027_lib.cli import main


def test_limit_flag_reaches_renderer():
    assert main(["--limit", "3", "report"]) == "report:3"


def test_default_limit_still_works():
    assert main(["report"]) == "report:10"
''',
        "hidden_test": '''from task_027_lib.cli import main


def test_uppercase_flag_reaches_renderer():
    assert main(["--uppercase", "report"]) == "REPORT:10"


def test_flags_can_be_combined():
    assert main(["--uppercase", "--limit", "2", "report"]) == "REPORT:2"
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The parser accepts flags, but `main` calls render with defaults.",
        "generalization_axis": "Public covers one propagated option; hidden covers another option and option composition.",
    },
    "task_028": {
        "bug_type": "sorting_filtering",
        "difficulty": "easy",
        "package": "task_028_lib",
        "files": {
            "task_028_lib/ranking.py": {
                "before": '''from __future__ import annotations


def active_names(users: list[dict], min_score: int = 0) -> list[str]:
    active = [user for user in users if user.get("active") and user.get("score", 0) >= min_score]
    return [user["name"] for user in sorted(active, key=lambda user: user["name"])]
''',
                "after": '''from __future__ import annotations


def active_names(users: list[dict], min_score: int = 0) -> list[str]:
    active = [user for user in users if user.get("active") and user.get("score", 0) >= min_score]
    ranked = sorted(active, key=lambda user: (-user.get("score", 0), user["name"]))
    return [user["name"] for user in ranked]
''',
            }
        },
        "target_files": ["task_028_lib/ranking.py"],
        "target_functions": ["active_names"],
        "issue": """# Rank active users by score

`active_names` should filter inactive users and low scores, then return names ordered by highest score first with name as a tie-breaker.

The current output looks fine for simple alphabetical fixtures but is wrong once scores are not already aligned with names.
""",
        "public_test": '''from task_028_lib.ranking import active_names


def test_filters_inactive_users():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Ben", "active": False, "score": 100},
        {"name": "Cal", "active": True, "score": 3},
    ]
    assert active_names(users) == ["Ada", "Cal"]


def test_applies_min_score():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Cal", "active": True, "score": 3},
    ]
    assert active_names(users, min_score=4) == ["Ada"]
''',
        "hidden_test": '''from task_028_lib.ranking import active_names


def test_sorts_by_score_descending():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Cal", "active": True, "score": 9},
        {"name": "Bea", "active": True, "score": 7},
    ]
    assert active_names(users) == ["Cal", "Bea", "Ada"]


def test_ties_sort_by_name():
    users = [
        {"name": "Zo", "active": True, "score": 5},
        {"name": "Al", "active": True, "score": 5},
    ]
    assert active_names(users) == ["Al", "Zo"]
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Filtering works, but ordering is alphabetical rather than score-descending.",
        "generalization_axis": "Public covers filtering; hidden covers the ranking rule.",
    },
    "task_029": {
        "bug_type": "error_handling",
        "difficulty": "easy",
        "package": "task_029_lib",
        "files": {
            "task_029_lib/parser.py": {
                "before": '''from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_timeout(config: dict) -> int:
    return int(config["timeout"])
''',
                "after": '''from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_timeout(config: dict) -> int:
    try:
        value = int(config["timeout"])
    except KeyError as exc:
        raise ConfigError("missing timeout") from exc
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout must be an integer") from exc
    if value <= 0:
        raise ConfigError("timeout must be positive")
    return value
''',
            }
        },
        "target_files": ["task_029_lib/parser.py"],
        "target_functions": ["parse_timeout"],
        "issue": """# Raise ConfigError for invalid timeouts

`parse_timeout` is part of config validation. It should return a positive integer timeout, and invalid configs should raise the local `ConfigError` type instead of leaking raw Python exceptions.

Please keep valid parsing behavior but normalize error handling.
""",
        "public_test": '''from task_029_lib.parser import ConfigError, parse_timeout


def test_valid_timeout_string():
    assert parse_timeout({"timeout": "30"}) == 30


def test_missing_timeout_raises_config_error():
    try:
        parse_timeout({})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
''',
        "hidden_test": '''from task_029_lib.parser import ConfigError, parse_timeout


def test_non_numeric_timeout_raises_config_error():
    try:
        parse_timeout({"timeout": "soon"})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")


def test_non_positive_timeout_raises_config_error():
    try:
        parse_timeout({"timeout": 0})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "Valid parsing works, but invalid inputs leak KeyError/ValueError or accept non-positive values.",
        "generalization_axis": "Public covers missing keys; hidden covers malformed and boundary values.",
    },
    "task_030": {
        "bug_type": "multi_file_integration",
        "difficulty": "medium",
        "package": "task_030_lib",
        "files": {
            "task_030_lib/tax.py": {
                "before": '''from __future__ import annotations


def tax_amount(subtotal: int, rate_percent: int) -> int:
    return subtotal * rate_percent // 100
''',
                "after": '''from __future__ import annotations


def tax_amount(subtotal: int, rate_percent: int) -> int:
    return round(subtotal * rate_percent / 100)
''',
            },
            "task_030_lib/invoice.py": {
                "before": '''from __future__ import annotations

from .tax import tax_amount


def subtotal(items: list[dict]) -> int:
    return sum(item["price"] * item.get("quantity", 1) for item in items)


def invoice_total(items: list[dict], rate_percent: int = 0) -> int:
    amount = subtotal(items)
    return amount
''',
                "after": '''from __future__ import annotations

from .tax import tax_amount


def subtotal(items: list[dict]) -> int:
    return sum(item["price"] * item.get("quantity", 1) for item in items)


def invoice_total(items: list[dict], rate_percent: int = 0) -> int:
    amount = subtotal(items)
    return amount + tax_amount(amount, rate_percent)
''',
            },
        },
        "target_files": ["task_030_lib/invoice.py", "task_030_lib/tax.py"],
        "target_functions": ["invoice_total", "tax_amount"],
        "issue": """# Invoice totals ignore tax helper behavior

The invoice service has a helper for tax calculation, but totals currently ignore tax entirely. The tax helper also truncates fractional tax amounts instead of applying normal rounding.

Please fix the integration so invoice totals include the rounded tax amount.
""",
        "public_test": '''from task_030_lib.invoice import invoice_total, subtotal


def test_subtotal_still_uses_quantity():
    assert subtotal([{"price": 10, "quantity": 2}, {"price": 5}]) == 25


def test_invoice_total_includes_simple_tax():
    assert invoice_total([{"price": 100}], rate_percent=10) == 110
''',
        "hidden_test": '''from task_030_lib.invoice import invoice_total
from task_030_lib.tax import tax_amount


def test_tax_amount_rounds_fractional_values():
    assert tax_amount(99, 5) == 5


def test_invoice_total_uses_rounded_tax():
    assert invoice_total([{"price": 99}], rate_percent=5) == 104
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "Invoice totals ignore tax and the helper truncates fractional tax.",
        "generalization_axis": "Public covers integration with whole-number tax; hidden covers helper rounding across files.",
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
    package_dir = task_dir / spec["package"]
    write(package_dir / "__init__.py", "")
    for rel, payload in spec["files"].items():
        write(task_dir / rel, payload["before"])
    write(task_dir / "issue.md", spec["issue"])
    write(task_dir / "tests" / f"test_{task_id}_public.py", spec["public_test"])
    write(task_dir / "tests_hidden" / f"test_{task_id}_hidden.py", spec["hidden_test"])
    write_metadata(task_dir, task_id, spec)
    regenerate_gold_patch(task_dir, spec)


def write_metadata(task_dir: Path, task_id: str, spec: dict) -> None:
    metadata = {
        "task_id": task_id,
        "bug_type": spec["bug_type"],
        "difficulty": spec["difficulty"],
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "target_files": spec["target_files"],
        "target_functions": spec["target_functions"],
        "expected_failure_mode": spec["expected_failure_mode"],
        "generalization_axis": spec["generalization_axis"],
        "repo_path": str(Path("data/mini_repo_debug/repos") / task_id),
        "source": "manual_p38_expansion",
        "split": "train",
        "scenario": f"{spec['bug_type']} public-hidden generalization",
        "gold_patch": "gold.patch",
        "gold_files": spec["target_files"],
        "gold_functions": spec["target_functions"],
        "forbidden_behaviors": [
            "hard-code public examples",
            "modify tests",
            "ignore hidden edge cases",
        ],
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
        for rel, payload in spec["files"].items():
            write(tmp / rel, payload["after"])
        proc = must_run(["git", "diff", "--binary"], tmp)
        patch = proc.stdout
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
    print("PASS: P38 task_026-task_030 repair and verification complete")


if __name__ == "__main__":
    main()
