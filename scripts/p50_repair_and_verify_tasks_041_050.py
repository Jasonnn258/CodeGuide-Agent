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
TASK_IDS = [f"task_{index:03d}" for index in range(41, 51)]


TASKS: dict[str, dict] = {
    "task_041": {
        "bug_type": "parsing_edge_case",
        "package": "task_041_lib",
        "files": {
            "task_041_lib/parser.py": (
                '''from __future__ import annotations


def parse_assignment(line: str) -> tuple[str, str]:
    key, value = line.split("=")
    return key.strip(), value.strip()
''',
                '''from __future__ import annotations


def parse_assignment(line: str) -> tuple[str, str]:
    key, value = line.split("=", 1)
    return key.strip(), value.strip()
''',
            )
        },
        "target_functions": ["parse_assignment"],
        "issue": """# Assignment parser rejects values containing equals signs

`parse_assignment` should split only on the first equals sign so configuration values such as tokens or URLs can contain `=` characters.
""",
        "public_test": '''from task_041_lib.parser import parse_assignment


def test_parses_simple_assignment():
    assert parse_assignment("host=localhost") == ("host", "localhost")


def test_strips_outer_whitespace():
    assert parse_assignment(" port = 5432 ") == ("port", "5432")
''',
        "hidden_test": '''from task_041_lib.parser import parse_assignment


def test_value_may_contain_equals():
    assert parse_assignment("token=a=b=c") == ("token", "a=b=c")
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Simple assignments parse, but values containing equals signs raise an unpacking error.",
        "generalization_axis": "Public covers normal assignments; hidden covers separator characters inside values.",
    },
    "task_042": {
        "bug_type": "path_handling",
        "package": "task_042_lib",
        "files": {
            "task_042_lib/paths.py": (
                '''from __future__ import annotations

from pathlib import PurePosixPath


def safe_asset_path(path: str) -> str:
    return str(PurePosixPath(path))
''',
                '''from __future__ import annotations

from pathlib import PurePosixPath


def safe_asset_path(path: str) -> str:
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError("asset path must stay inside the asset root")
    return str(normalized)
''',
            )
        },
        "target_functions": ["safe_asset_path"],
        "issue": """# Asset paths must stay inside the asset root

`safe_asset_path` should normalize ordinary relative paths, but reject absolute paths and parent-directory traversal.
""",
        "public_test": '''from task_042_lib.paths import safe_asset_path


def test_keeps_simple_relative_path():
    assert safe_asset_path("images/logo.png") == "images/logo.png"


def test_normalizes_current_directory():
    assert safe_asset_path("images/./logo.png") == "images/logo.png"
''',
        "hidden_test": '''from task_042_lib.paths import safe_asset_path


def test_rejects_parent_traversal():
    try:
        safe_asset_path("../secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rejects_absolute_path():
    try:
        safe_asset_path("/tmp/secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Normal relative paths work, but unsafe absolute and traversal paths are accepted.",
        "generalization_axis": "Public covers normalization; hidden covers path containment.",
    },
    "task_043": {
        "bug_type": "cache_key",
        "package": "task_043_lib",
        "files": {
            "task_043_lib/cache.py": (
                '''from __future__ import annotations

import json


def make_cache_key(name: str, args: tuple = (), kwargs: dict | None = None) -> str:
    return json.dumps({"name": name, "args": args}, sort_keys=True)
''',
                '''from __future__ import annotations

import json


def make_cache_key(name: str, args: tuple = (), kwargs: dict | None = None) -> str:
    return json.dumps({"name": name, "args": args, "kwargs": kwargs or {}}, sort_keys=True)
''',
            )
        },
        "target_functions": ["make_cache_key"],
        "issue": """# Cache keys ignore keyword arguments

`make_cache_key` should produce different keys when keyword arguments differ, while remaining stable when kwargs are supplied in a different order.
""",
        "public_test": '''from task_043_lib.cache import make_cache_key


def test_kwargs_affect_cache_key():
    assert make_cache_key("load", kwargs={"page": 1}) != make_cache_key("load", kwargs={"page": 2})


def test_kwargs_order_is_stable():
    assert make_cache_key("load", kwargs={"a": 1, "b": 2}) == make_cache_key("load", kwargs={"b": 2, "a": 1})
''',
        "hidden_test": '''from task_043_lib.cache import make_cache_key


def test_args_and_kwargs_are_both_preserved():
    assert make_cache_key("load", args=("users",), kwargs={"limit": 10}) != make_cache_key(
        "load", args=("users",), kwargs={"limit": 20}
    )
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The key includes positional args but drops keyword arguments.",
        "generalization_axis": "Public covers kwargs identity; hidden covers mixed args and kwargs.",
    },
    "task_044": {
        "bug_type": "optional_default_args",
        "package": "task_044_lib",
        "files": {
            "task_044_lib/options.py": (
                '''from __future__ import annotations


def add_flag(flag: str, flags: list[str] = []) -> list[str]:
    flags.append(flag)
    return flags
''',
                '''from __future__ import annotations


def add_flag(flag: str, flags: list[str] | None = None) -> list[str]:
    result = list(flags) if flags is not None else []
    result.append(flag)
    return result
''',
            )
        },
        "target_functions": ["add_flag"],
        "issue": """# Optional flag list leaks state

`add_flag` should create a fresh list when no list is supplied and should not mutate caller-provided lists.
""",
        "public_test": '''from task_044_lib.options import add_flag


def test_default_flags_are_independent():
    assert add_flag("--debug") == ["--debug"]
    assert add_flag("--quiet") == ["--quiet"]
''',
        "hidden_test": '''from task_044_lib.options import add_flag


def test_input_flags_are_not_mutated():
    existing = ["--json"]
    result = add_flag("--verbose", existing)
    assert result == ["--json", "--verbose"]
    assert existing == ["--json"]
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "A mutable default is shared and explicit caller lists are modified in place.",
        "generalization_axis": "Public covers default leakage; hidden covers input mutation.",
    },
    "task_045": {
        "bug_type": "boundary_condition",
        "package": "task_045_lib",
        "files": {
            "task_045_lib/windows.py": (
                '''from __future__ import annotations


def take_window(values: list[int], start: int, size: int) -> list[int]:
    if start + size >= len(values):
        return []
    return values[start : start + size]
''',
                '''from __future__ import annotations


def take_window(values: list[int], start: int, size: int) -> list[int]:
    if size < 0 or start < 0:
        return []
    if start + size > len(values):
        return []
    return values[start : start + size]
''',
            )
        },
        "target_functions": ["take_window"],
        "issue": """# Window helper drops exact boundary slices

`take_window` should allow a slice that ends exactly at the end of the list, but reject windows that overrun the list.
""",
        "public_test": '''from task_045_lib.windows import take_window


def test_window_inside_list():
    assert take_window([1, 2, 3, 4], 1, 2) == [2, 3]


def test_rejects_overrun():
    assert take_window([1, 2, 3], 2, 2) == []
''',
        "hidden_test": '''from task_045_lib.windows import take_window


def test_exact_end_boundary_is_allowed():
    assert take_window([1, 2, 3], 1, 2) == [2, 3]
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Internal windows and overruns work, but exact-end windows are rejected.",
        "generalization_axis": "Public covers interior and overrun windows; hidden covers exact boundary behavior.",
    },
    "task_046": {
        "bug_type": "string_normalization",
        "package": "task_046_lib",
        "files": {
            "task_046_lib/slugs.py": (
                '''from __future__ import annotations


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "-")
''',
                '''from __future__ import annotations

import re


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")
''',
            )
        },
        "target_functions": ["slugify"],
        "issue": """# Slug normalization leaves punctuation artifacts

`slugify` should normalize repeated whitespace and punctuation to single dashes, with no leading or trailing dash.
""",
        "public_test": '''from task_046_lib.slugs import slugify


def test_simple_words():
    assert slugify("Hello World") == "hello-world"


def test_outer_whitespace():
    assert slugify("  Alpha  ") == "alpha"
''',
        "hidden_test": '''from task_046_lib.slugs import slugify


def test_punctuation_and_repeated_spaces():
    assert slugify("Hello,   World!") == "hello-world"
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Basic space replacement works, but punctuation and repeated separators are not normalized.",
        "generalization_axis": "Public covers simple normalization; hidden covers punctuation and repeated separators.",
    },
    "task_047": {
        "bug_type": "dict_mutation",
        "package": "task_047_lib",
        "files": {
            "task_047_lib/profiles.py": (
                '''from __future__ import annotations


def with_status(profile: dict, status: str) -> dict:
    profile["status"] = status
    return profile
''',
                '''from __future__ import annotations


def with_status(profile: dict, status: str) -> dict:
    updated = dict(profile)
    updated["status"] = status
    return updated
''',
            )
        },
        "target_functions": ["with_status"],
        "issue": """# Profile status helper mutates callers

`with_status` should return an updated profile without changing the input dictionary owned by the caller.
""",
        "public_test": '''from task_047_lib.profiles import with_status


def test_returns_updated_profile():
    assert with_status({"name": "Ada"}, "active") == {"name": "Ada", "status": "active"}


def test_original_profile_is_unchanged():
    profile = {"name": "Ada"}
    with_status(profile, "active")
    assert profile == {"name": "Ada"}
''',
        "hidden_test": '''from task_047_lib.profiles import with_status


def test_existing_status_is_replaced_on_copy():
    profile = {"name": "Ada", "status": "pending"}
    result = with_status(profile, "active")
    assert result == {"name": "Ada", "status": "active"}
    assert profile == {"name": "Ada", "status": "pending"}
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The returned value is correct, but the original dictionary is mutated.",
        "generalization_axis": "Public covers mutation safety; hidden covers replacement without aliasing.",
    },
    "task_048": {
        "bug_type": "date_boundary",
        "package": "task_048_lib",
        "files": {
            "task_048_lib/dates.py": (
                '''from __future__ import annotations

from datetime import date


def is_due(due_on: date, today: date) -> bool:
    return due_on < today
''',
                '''from __future__ import annotations

from datetime import date


def is_due(due_on: date, today: date) -> bool:
    return due_on <= today
''',
            )
        },
        "target_functions": ["is_due"],
        "issue": """# Due-date check misses items due today

`is_due` should return true for items due before today and for items due today.
""",
        "public_test": '''from datetime import date

from task_048_lib.dates import is_due


def test_past_date_is_due():
    assert is_due(date(2026, 1, 1), date(2026, 1, 2)) is True


def test_future_date_is_not_due():
    assert is_due(date(2026, 1, 3), date(2026, 1, 2)) is False
''',
        "hidden_test": '''from datetime import date

from task_048_lib.dates import is_due


def test_due_today_is_due():
    assert is_due(date(2026, 1, 2), date(2026, 1, 2)) is True
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Past and future dates classify correctly, but today is treated as not due.",
        "generalization_axis": "Public covers strict past/future; hidden covers equality boundary.",
    },
    "task_049": {
        "bug_type": "json_config_parsing",
        "package": "task_049_lib",
        "files": {
            "task_049_lib/config.py": (
                '''from __future__ import annotations

import json


def is_enabled(raw_json: str) -> bool:
    config = json.loads(raw_json)
    return bool(config.get("enabled", False))
''',
                '''from __future__ import annotations

import json


def is_enabled(raw_json: str) -> bool:
    config = json.loads(raw_json)
    value = config.get("enabled", False)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
''',
            )
        },
        "target_functions": ["is_enabled"],
        "issue": """# JSON config parser treats string false as enabled

`is_enabled` should support boolean values and common string values, but the string `"false"` must not become true just because it is non-empty.
""",
        "public_test": '''from task_049_lib.config import is_enabled


def test_boolean_true():
    assert is_enabled('{"enabled": true}') is True


def test_boolean_false():
    assert is_enabled('{"enabled": false}') is False
''',
        "hidden_test": '''from task_049_lib.config import is_enabled


def test_string_false_is_disabled():
    assert is_enabled('{"enabled": "false"}') is False


def test_string_yes_is_enabled():
    assert is_enabled('{"enabled": "yes"}') is True
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "JSON booleans work, but string false is treated as truthy.",
        "generalization_axis": "Public covers native booleans; hidden covers string configuration values.",
    },
    "task_050": {
        "bug_type": "cli_argument_propagation",
        "package": "task_050_lib",
        "files": {
            "task_050_lib/cli.py": (
                '''from __future__ import annotations

import argparse


def render(name: str, prefix: str = "Hello") -> str:
    return f"{prefix}, {name}!"


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--prefix", default="Hello")
    args = parser.parse_args(argv)
    return render(args.name)
''',
                '''from __future__ import annotations

import argparse


def render(name: str, prefix: str = "Hello") -> str:
    return f"{prefix}, {name}!"


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--prefix", default="Hello")
    args = parser.parse_args(argv)
    return render(args.name, prefix=args.prefix)
''',
            )
        },
        "target_functions": ["main", "render"],
        "issue": """# CLI prefix argument is parsed but ignored

The CLI accepts `--prefix`, but `main` never passes it into `render`, so custom greetings are dropped.
""",
        "public_test": '''from task_050_lib.cli import main


def test_custom_prefix_is_used():
    assert main(["Ada", "--prefix", "Hi"]) == "Hi, Ada!"


def test_default_prefix_still_works():
    assert main(["Ada"]) == "Hello, Ada!"
''',
        "hidden_test": '''from task_050_lib.cli import main


def test_multi_word_prefix_is_used():
    assert main(["Ada", "--prefix", "Good morning"]) == "Good morning, Ada!"
''',
        "expected_buggy": ("fail", "fail"),
        "expected_failure_mode": "The argument parser accepts prefix, but the value is not propagated.",
        "generalization_axis": "Public covers propagation; hidden covers a multi-word argument value.",
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
        "source": "manual_p50_expansion",
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
    print("PASS: P50 task_041-task_050 repair and verification complete")


if __name__ == "__main__":
    main()
