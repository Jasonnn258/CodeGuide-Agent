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
TASK_IDS = [f"task_{index:03d}" for index in range(51, 61)]


TASKS: dict[str, dict] = {
    "task_051": {
        "bug_type": "error_handling",
        "package": "task_051_lib",
        "files": {
            "task_051_lib/parser.py": (
                '''from __future__ import annotations


def parse_int(value) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
''',
                '''from __future__ import annotations


def parse_int(value) -> int | None:
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    try:
        return int(value)
    except ValueError:
        return None
''',
            )
        },
        "target_functions": ["parse_int"],
        "issue": """# Integer parser swallows type errors

`parse_int` should convert numeric strings to integers and return `None` for unparseable strings, but must raise `TypeError` when the input is not a string at all.
""",
        "public_test": '''from task_051_lib.parser import parse_int


def test_parses_integer_string():
    assert parse_int("42") == 42


def test_returns_none_for_garbage():
    assert parse_int("abc") is None
''',
        "hidden_test": '''from task_051_lib.parser import parse_int


def test_rejects_non_string():
    try:
        parse_int(None)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for None input")


def test_rejects_list_input():
    try:
        parse_int([1, 2, 3])
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for list input")
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Numeric strings parse correctly, but non-string types return None instead of raising TypeError.",
        "generalization_axis": "Public covers valid and invalid strings; hidden covers type validation.",
    },
    "task_052": {
        "bug_type": "numeric_edge_case",
        "package": "task_052_lib",
        "files": {
            "task_052_lib/temperature.py": (
                '''from __future__ import annotations


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9 // 5 + 32
''',
                '''from __future__ import annotations


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9.0 / 5.0 + 32
''',
            )
        },
        "target_functions": ["celsius_to_fahrenheit"],
        "issue": """# Temperature conversion loses precision

`celsius_to_fahrenheit` should return accurate floating-point results for all Celsius values, but integer division truncates the fractional part.
""",
        "public_test": '''from task_052_lib.temperature import celsius_to_fahrenheit


def test_freezing_point():
    assert celsius_to_fahrenheit(0) == 32


def test_boiling_point():
    assert celsius_to_fahrenheit(100) == 212
''',
        "hidden_test": '''from task_052_lib.temperature import celsius_to_fahrenheit


def test_one_degree_is_not_integer_fahrenheit():
    assert celsius_to_fahrenheit(1) == 33.8


def test_negative_temperature_precision():
    assert celsius_to_fahrenheit(-40) == -40.0
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Values that divide evenly work, but fractional results are truncated by integer division.",
        "generalization_axis": "Public covers multiples of 5 that divide evenly; hidden covers values that require floating-point precision.",
    },
    "task_053": {
        "bug_type": "sorting_filtering",
        "package": "task_053_lib",
        "files": {
            "task_053_lib/sorting.py": (
                '''from __future__ import annotations


def sort_names(names: list[str]) -> list[str]:
    return sorted(names)
''',
                '''from __future__ import annotations


def sort_names(names: list[str]) -> list[str]:
    return sorted(names, key=str.lower)
''',
            )
        },
        "target_functions": ["sort_names"],
        "issue": """# Name sorter is case-sensitive

`sort_names` should sort names case-insensitively so that "alice" and "Bob" are ordered by their letters regardless of capitalization.
""",
        "public_test": '''from task_053_lib.sorting import sort_names


def test_sorts_lowercase_names():
    assert sort_names(["bob", "alice", "charlie"]) == ["alice", "bob", "charlie"]


def test_sorts_numeric_prefixes():
    assert sort_names(["v2", "v1", "v10"]) == ["v1", "v10", "v2"]
''',
        "hidden_test": '''from task_053_lib.sorting import sort_names


def test_sorts_case_insensitively():
    assert sort_names(["Bob", "alice", "Charlie"]) == ["alice", "Bob", "Charlie"]


def test_mixed_case_stable():
    assert sort_names(["CAR", "apple", "banana"]) == ["apple", "banana", "CAR"]
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "All-lowercase names sort correctly, but mixed-case names are sorted by ASCII order instead of case-insensitively.",
        "generalization_axis": "Public covers homogeneous-case inputs; hidden covers mixed-case inputs.",
    },
    "task_054": {
        "bug_type": "service_helper_integration",
        "package": "task_054_lib",
        "files": {
            "task_054_lib/pipeline.py": (
                '''from __future__ import annotations

from collections.abc import Callable


def build_pipeline(steps: list[Callable]) -> Callable:
    def run(data):
        result = data
        for step in steps:
            result = step(result)
            break
        return result

    return run
''',
                '''from __future__ import annotations

from collections.abc import Callable


def build_pipeline(steps: list[Callable]) -> Callable:
    def run(data):
        result = data
        for step in steps:
            result = step(result)
        return result

    return run
''',
            )
        },
        "target_functions": ["build_pipeline"],
        "issue": """# Pipeline builder only runs the first step

`build_pipeline` should chain every step so each step receives the output of the previous step, but the loop exits after the first iteration.
""",
        "public_test": '''from task_054_lib.pipeline import build_pipeline


def test_single_step_pipeline():
    double = build_pipeline([lambda x: x * 2])
    assert double(5) == 10


def test_single_step_identity():
    identity = build_pipeline([lambda x: x])
    assert identity("hello") == "hello"
''',
        "hidden_test": '''from task_054_lib.pipeline import build_pipeline


def test_two_step_pipeline():
    pipe = build_pipeline([lambda x: x + 1, lambda x: x * 3])
    assert pipe(5) == 18


def test_three_step_pipeline():
    pipe = build_pipeline([str, lambda s: s.upper(), lambda s: f"({s})"])
    assert pipe(42) == "(42)"
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Single-step pipelines work, but multi-step pipelines only execute the first step.",
        "generalization_axis": "Public covers single-step pipelines; hidden covers multi-step chaining.",
    },
    "task_055": {
        "bug_type": "case_insensitive_handling",
        "package": "task_055_lib",
        "files": {
            "task_055_lib/tags.py": (
                '''from __future__ import annotations


def normalize_tag(tag: str) -> str:
    return tag.lower()
''',
                '''from __future__ import annotations


def normalize_tag(tag: str) -> str:
    return tag.strip().lower()
''',
            )
        },
        "target_functions": ["normalize_tag"],
        "issue": """# Tag normalizer keeps surrounding whitespace

`normalize_tag` should lowercase the tag and remove leading and trailing whitespace so that "  Python  " and "python" are treated as the same tag.
""",
        "public_test": '''from task_055_lib.tags import normalize_tag


def test_lowercases_uppercase():
    assert normalize_tag("Python") == "python"


def test_preserves_lowercase():
    assert normalize_tag("rust") == "rust"
''',
        "hidden_test": '''from task_055_lib.tags import normalize_tag


def test_strips_leading_whitespace():
    assert normalize_tag("  Go") == "go"


def test_strips_trailing_whitespace():
    assert normalize_tag("Rust  ") == "rust"


def test_strips_both_sides():
    assert normalize_tag("  Python  ") == "python"
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Lowercasing works, but surrounding whitespace is preserved.",
        "generalization_axis": "Public covers case conversion; hidden covers whitespace stripping.",
    },
    "task_056": {
        "bug_type": "multi_file_integration",
        "package": "task_056_lib",
        "files": {
            "task_056_lib/__init__.py": (
                "",
                "",
            ),
            "task_056_lib/helpers.py": (
                '''from __future__ import annotations


def aggregate(values: list[float]) -> dict:
    return {"sum": sum(values), "count": len(values)}
''',
                '''from __future__ import annotations


def aggregate(values: list[float]) -> dict:
    if not values:
        return {"sum": 0.0, "count": 0}
    return {"sum": sum(values), "count": len(values)}
''',
            ),
            "task_056_lib/stats.py": (
                '''from __future__ import annotations

from task_056_lib.helpers import aggregate


def report(values: list[float]) -> dict:
    result = aggregate(values)
    result["mean"] = result["sum"] / result["count"]
    return result
''',
                '''from __future__ import annotations

from task_056_lib.helpers import aggregate


def report(values: list[float]) -> dict:
    result = aggregate(values)
    if result["count"] == 0:
        result["mean"] = 0.0
    else:
        result["mean"] = result["sum"] / result["count"]
    return result
''',
            ),
        },
        "target_functions": ["aggregate", "report"],
        "issue": """# Stats report crashes on empty input

`report` should return zeroed statistics for an empty list, but `aggregate` returns a count of zero, causing a division by zero when computing the mean.
""",
        "public_test": '''from task_056_lib.stats import report


def test_report_with_values():
    result = report([1.0, 2.0, 3.0])
    assert result["sum"] == 6.0
    assert result["count"] == 3
    assert result["mean"] == 2.0


def test_report_single_value():
    result = report([42.0])
    assert result["sum"] == 42.0
    assert result["count"] == 1
    assert result["mean"] == 42.0
''',
        "hidden_test": '''from task_056_lib.stats import report


def test_report_empty_list_returns_zeros():
    result = report([])
    assert result["sum"] == 0.0
    assert result["count"] == 0
    assert result["mean"] == 0.0
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Non-empty lists work, but empty input causes ZeroDivisionError.",
        "generalization_axis": "Public covers populated inputs; hidden covers the empty-list edge case.",
    },
    "task_057": {
        "bug_type": "stateful_side_effect",
        "package": "task_057_lib",
        "files": {
            "task_057_lib/counter.py": (
                '''from __future__ import annotations


class HitCounter:
    def __init__(self, limit: int = 100) -> None:
        self.count = 0
        self.limit = limit
        self.overflow = False

    def hit(self) -> None:
        self.count += 1
        if self.count > self.limit:
            self.overflow = True

    def reset(self) -> None:
        self.count = 0
''',
                '''from __future__ import annotations


class HitCounter:
    def __init__(self, limit: int = 100) -> None:
        self.count = 0
        self.limit = limit
        self.overflow = False

    def hit(self) -> None:
        self.count += 1
        if self.count > self.limit:
            self.overflow = True

    def reset(self) -> None:
        self.count = 0
        self.overflow = False
''',
            )
        },
        "target_functions": ["HitCounter.hit", "HitCounter.reset"],
        "issue": """# HitCounter reset leaves overflow flag set

`HitCounter.reset` should restore the counter to its initial state, including clearing the overflow flag, but it only resets the count.
""",
        "public_test": '''from task_057_lib.counter import HitCounter


def test_hit_increments_count():
    c = HitCounter(limit=10)
    c.hit()
    c.hit()
    assert c.count == 2


def test_reset_zeroes_count():
    c = HitCounter(limit=10)
    c.hit()
    c.hit()
    c.reset()
    assert c.count == 0


def test_no_overflow_within_limit():
    c = HitCounter(limit=10)
    for _ in range(10):
        c.hit()
    assert c.overflow is False
''',
        "hidden_test": '''from task_057_lib.counter import HitCounter


def test_reset_clears_overflow_flag():
    c = HitCounter(limit=2)
    c.hit()
    c.hit()
    c.hit()
    assert c.overflow is True
    c.reset()
    assert c.overflow is False


def test_reset_allows_fresh_overflow():
    c = HitCounter(limit=2)
    for _ in range(3):
        c.hit()
    c.reset()
    for _ in range(3):
        c.hit()
    assert c.overflow is True
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Count increment and reset work, but the overflow flag survives reset.",
        "generalization_axis": "Public covers basic count/reset; hidden covers overflow flag lifecycle.",
    },
    "task_058": {
        "bug_type": "idempotency",
        "package": "task_058_lib",
        "files": {
            "task_058_lib/fs.py": (
                '''from __future__ import annotations

import os


def ensure_dir(path: str) -> None:
    os.makedirs(path)
''',
                '''from __future__ import annotations

import os


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
''',
            )
        },
        "target_functions": ["ensure_dir"],
        "issue": """# ensure_dir is not idempotent

`ensure_dir` should safely create a directory and succeed silently when the directory already exists, but it raises an error on the second call.
""",
        "public_test": '''import tempfile
from pathlib import Path

from task_058_lib.fs import ensure_dir


def test_creates_new_directory():
    with tempfile.TemporaryDirectory() as td:
        new_dir = Path(td) / "subdir"
        ensure_dir(str(new_dir))
        assert new_dir.is_dir()
''',
        "hidden_test": '''import tempfile
from pathlib import Path

from task_058_lib.fs import ensure_dir


def test_calling_twice_is_safe():
    with tempfile.TemporaryDirectory() as td:
        new_dir = Path(td) / "subdir"
        ensure_dir(str(new_dir))
        ensure_dir(str(new_dir))
        assert new_dir.is_dir()
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "First call succeeds, but the second call on the same path raises FileExistsError.",
        "generalization_axis": "Public covers single creation; hidden covers idempotent re-invocation.",
    },
    "task_059": {
        "bug_type": "validation_logic",
        "package": "task_059_lib",
        "files": {
            "task_059_lib/validators.py": (
                '''from __future__ import annotations


def is_valid_username(name: str) -> bool:
    return len(name) >= 3 and name.isalnum()
''',
                '''from __future__ import annotations


def is_valid_username(name: str) -> bool:
    cleaned = name.strip()
    return len(cleaned) >= 3 and cleaned.isalnum()
''',
            )
        },
        "target_functions": ["is_valid_username"],
        "issue": """# Username validator rejects names with surrounding whitespace

`is_valid_username` should accept names that are valid after trimming whitespace, but it treats leading or trailing spaces as invalid characters.
""",
        "public_test": '''from task_059_lib.validators import is_valid_username


def test_valid_username_accepted():
    assert is_valid_username("alice") is True


def test_too_short_username_rejected():
    assert is_valid_username("ab") is False


def test_special_characters_rejected():
    assert is_valid_username("bad!") is False
''',
        "hidden_test": '''from task_059_lib.validators import is_valid_username


def test_trims_leading_whitespace():
    assert is_valid_username("  alice") is True


def test_trims_trailing_whitespace():
    assert is_valid_username("bob  ") is True


def test_whitespace_only_is_rejected():
    assert is_valid_username("   ") is False
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Valid names and invalid short names work, but whitespace-padded valid names are incorrectly rejected.",
        "generalization_axis": "Public covers valid/invalid strings; hidden covers whitespace normalization.",
    },
    "task_060": {
        "bug_type": "config_merge",
        "package": "task_060_lib",
        "files": {
            "task_060_lib/config.py": (
                '''from __future__ import annotations


def merge_config(base: dict, override: dict) -> dict:
    result = dict(base)
    result.update(override)
    return result
''',
                '''from __future__ import annotations


def merge_config(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
''',
            )
        },
        "target_functions": ["merge_config"],
        "issue": """# Config merge overwrites nested sections

`merge_config` should deep-merge nested dictionaries so that overriding a single key inside a nested section preserves sibling keys, but the current flat update replaces the entire subsection.
""",
        "public_test": '''from task_060_lib.config import merge_config


def test_flat_merge_adds_new_key():
    base = {"host": "localhost"}
    override = {"port": 5432}
    result = merge_config(base, override)
    assert result == {"host": "localhost", "port": 5432}


def test_flat_merge_overwrites_existing_key():
    base = {"host": "localhost", "port": 8080}
    override = {"port": 5432}
    result = merge_config(base, override)
    assert result["port"] == 5432
''',
        "hidden_test": '''from task_060_lib.config import merge_config


def test_deep_merge_preserves_sibling_keys():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"host": "prod-host"}}
    result = merge_config(base, override)
    assert result["db"]["host"] == "prod-host"
    assert result["db"]["port"] == 5432


def test_deep_merge_adds_nested_key():
    base = {"server": {"name": "main"}}
    override = {"server": {"timeout": 30}}
    result = merge_config(base, override)
    assert result["server"]["name"] == "main"
    assert result["server"]["timeout"] == 30
''',
        "expected_buggy": ("pass", "fail"),
        "expected_failure_mode": "Flat key-value pairs merge correctly, but nested dicts are replaced instead of deep-merged.",
        "generalization_axis": "Public covers flat config merge; hidden covers nested deep merge.",
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
        if rel.endswith("__init__.py"):
            continue
        write(task_dir / rel, before)
    write(task_dir / "issue.md", spec["issue"])
    write(task_dir / "tests" / f"test_{task_id}_public.py", spec["public_test"])
    write(task_dir / "tests_hidden" / f"test_{task_id}_hidden.py", spec["hidden_test"])
    write_metadata(task_dir, task_id, spec)
    regenerate_gold_patch(task_dir, spec)


def write_metadata(task_dir: Path, task_id: str, spec: dict) -> None:
    target_files = [rel for rel in spec["files"].keys() if not rel.endswith("__init__.py")]
    metadata = {
        "task_id": task_id,
        "bug_type": spec["bug_type"],
        "difficulty": "easy",
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "target_files": target_files,
        "target_functions": spec["target_functions"],
        "expected_failure_mode": spec["expected_failure_mode"],
        "generalization_axis": spec["generalization_axis"],
        "repo_path": str(Path("data/mini_repo_debug/repos") / task_id),
        "source": "manual_p55_expansion",
        "split": "train",
        "scenario": f"{spec['bug_type']} public-hidden generalization",
        "gold_patch": "gold.patch",
        "gold_files": target_files,
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
            if rel.endswith("__init__.py"):
                continue
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
    hard_pair = "HARD_PAIR" if (actual_public == "pass" and actual_hidden == "fail") else "STANDARD"
    print(f"PASS {task_id}: buggy public={actual_public}, buggy hidden={actual_hidden}, gold=pass [{hard_pair}]")


def main() -> None:
    for task_id in TASK_IDS:
        write_task(task_id, TASKS[task_id])
        check_patch_applies(task_id)
    hard_pair_count = 0
    for task_id in TASK_IDS:
        verify_task(task_id, TASKS[task_id])
        spec = TASKS[task_id]
        if spec["expected_buggy"] == ("pass", "fail"):
            hard_pair_count += 1
    print(f"\nPASS: P55 task_051-task_060 repair and verification complete")
    print(f"Hard-pair tasks: {hard_pair_count}/10")


if __name__ == "__main__":
    main()
