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
TASK_IDS = [f"task_{index:03d}" for index in range(61, 101)]

# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

TASKS: dict[str, dict] = {}

# ---- Block 1: 061-070 (medium, P50 bug types) ----

TASKS["task_061"] = {
    "bug_type": "parsing_edge_case",
    "package": "task_061_lib",
    "files": {
        "task_061_lib/version.py": (
            '''from __future__ import annotations


def parse_version(version_str: str) -> tuple[int, ...]:
    parts = version_str.split(".")
    return tuple(int(p) for p in parts)
''',
            '''from __future__ import annotations


def parse_version(version_str: str) -> tuple[int, ...]:
    clean = version_str.split("-")[0]
    parts = clean.split(".")
    return tuple(int(p) for p in parts)
''',
        )
    },
    "target_functions": ["parse_version"],
    "issue": """# Version parser crashes on pre-release suffixes

`parse_version` should strip pre-release labels such as `-beta` or `-rc1` before parsing the numeric parts.
""",
    "public_test": '''from task_061_lib.version import parse_version


def test_stable_version():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_zero_version():
    assert parse_version("0.0.1") == (0, 0, 1)
''',
    "hidden_test": '''from task_061_lib.version import parse_version


def test_prerelease_suffix_is_stripped():
    assert parse_version("1.2.3-beta") == (1, 2, 3)


def test_rc_suffix_is_stripped():
    assert parse_version("2.0.0-rc1") == (2, 0, 0)
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Stable versions parse correctly, but pre-release suffixes cause ValueError.",
    "generalization_axis": "Public covers stable semver; hidden covers pre-release labels.",
}

TASKS["task_062"] = {
    "bug_type": "path_handling",
    "package": "task_062_lib",
    "files": {
        "task_062_lib/resolve.py": (
            '''from __future__ import annotations


def resolve_path(base: str, relative: str) -> str:
    if relative.startswith("/"):
        return relative
    return base.rstrip("/") + "/" + relative
''',
            '''from __future__ import annotations


def resolve_path(base: str, relative: str) -> str:
    if relative.startswith("/"):
        return relative
    parts = relative.split("/")
    base_parts = [p for p in base.split("/") if p]
    for part in parts:
        if part == "..":
            if base_parts:
                base_parts.pop()
        elif part and part != ".":
            base_parts.append(part)
    return "/" + "/".join(base_parts)
''',
        )
    },
    "target_functions": ["resolve_path"],
    "issue": """# Path resolver does not collapse parent-directory references

`resolve_path` should normalize `..` segments so that `/a/b/../c` resolves to `/a/c`. Going above the root should be clamped.
""",
    "public_test": '''from task_062_lib.resolve import resolve_path


def test_simple_child():
    assert resolve_path("/a/b", "c") == "/a/b/c"


def test_absolute_override():
    assert resolve_path("/a/b", "/x/y") == "/x/y"
''',
    "hidden_test": '''from task_062_lib.resolve import resolve_path


def test_parent_is_resolved():
    assert resolve_path("/a/b/c", "../d") == "/a/b/d"


def test_double_parent_is_resolved():
    assert resolve_path("/a/b/c", "../../x") == "/a/x"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Simple joins work, but `..` segments are left in the path literally.",
    "generalization_axis": "Public covers simple appending; hidden covers parent-directory normalization.",
}

TASKS["task_063"] = {
    "bug_type": "cache_key",
    "package": "task_063_lib",
    "files": {
        "task_063_lib/keys.py": (
            '''from __future__ import annotations


def make_cache_key(func_name: str, *args: object) -> str:
    return func_name + ":" + ":".join(str(a) for a in args)
''',
            '''from __future__ import annotations


def make_cache_key(func_name: str, *args: object) -> str:
    return func_name + ":" + ":".join(
        f"{type(a).__name__}:{a}" for a in args
    )
''',
        )
    },
    "target_functions": ["make_cache_key"],
    "issue": """# Cache key ignores argument types

`make_cache_key` should produce different keys for values that compare equal but have different types, such as the integer `1` and the float `1.0`.
""",
    "public_test": '''from task_063_lib.keys import make_cache_key


def test_different_values_produce_different_keys():
    assert make_cache_key("add", 1, 2) != make_cache_key("add", 1, 3)


def test_different_names_produce_different_keys():
    assert make_cache_key("add", 1, 2) != make_cache_key("sub", 1, 2)
''',
    "hidden_test": '''from task_063_lib.keys import make_cache_key


def test_int_vs_float_produce_different_keys():
    assert make_cache_key("f", 1) != make_cache_key("f", 1.0)


def test_string_vs_int_produce_different_keys():
    assert make_cache_key("f", "42") != make_cache_key("f", 42)
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Different values work, but types are not encoded so int/float collisions happen.",
    "generalization_axis": "Public covers value identity; hidden covers type identity.",
}

TASKS["task_064"] = {
    "bug_type": "optional_default_args",
    "package": "task_064_lib",
    "files": {
        "task_064_lib/query.py": (
            '''from __future__ import annotations


def build_query(**params: object) -> str:
    parts = [f"{k}={v}" for k, v in params.items()]
    return "&".join(parts)
''',
            '''from __future__ import annotations


def build_query(**params: object) -> str:
    parts = [f"{k}={v}" for k, v in params.items() if v is not None]
    return "&".join(parts)
''',
        )
    },
    "target_functions": ["build_query"],
    "issue": """# Query builder includes None values

`build_query` should skip keyword arguments whose value is `None` so that optional parameters are cleanly omitted.
""",
    "public_test": '''from task_064_lib.query import build_query


def test_all_parameters_present():
    assert build_query(a=1, b=2) == "a=1&b=2"


def test_single_parameter():
    assert build_query(q="search") == "q=search"
''',
    "hidden_test": '''from task_064_lib.query import build_query


def test_none_values_are_skipped():
    assert build_query(a=1, b=None) == "a=1"


def test_all_none_returns_empty():
    assert build_query(x=None, y=None) == ""
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Explicit values work, but None-valued parameters appear as 'None'.",
    "generalization_axis": "Public covers explicit values; hidden covers None filtering.",
}

TASKS["task_065"] = {
    "bug_type": "boundary_condition",
    "package": "task_065_lib",
    "files": {
        "task_065_lib/pages.py": (
            '''from __future__ import annotations


def page_count(total: int, per_page: int) -> int:
    return total // per_page
''',
            '''from __future__ import annotations


def page_count(total: int, per_page: int) -> int:
    return (total + per_page - 1) // per_page
''',
        )
    },
    "target_functions": ["page_count"],
    "issue": """# Page count drops trailing items

`page_count` should return the ceiling of `total / per_page` so that a partial last page counts as a full page.
""",
    "public_test": '''from task_065_lib.pages import page_count


def test_exact_multiple():
    assert page_count(100, 10) == 10


def test_multiple_pages():
    assert page_count(200, 10) == 20


def test_zero_items():
    assert page_count(0, 10) == 0
''',
    "hidden_test": '''from task_065_lib.pages import page_count


def test_partial_last_page_counts():
    assert page_count(21, 10) == 3


def test_one_over_boundary():
    assert page_count(11, 10) == 2


def test_less_than_page_size_counts_as_one():
    assert page_count(5, 10) == 1
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Exact multiples work, but a partial page is truncated.",
    "generalization_axis": "Public covers exact divisor cases; hidden covers ceiling boundary.",
}

TASKS["task_066"] = {
    "bug_type": "string_normalization",
    "package": "task_066_lib",
    "files": {
        "task_066_lib/whitespace.py": (
            '''from __future__ import annotations


def collapse_whitespace(text: str) -> str:
    result = text.replace("  ", " ")
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()
''',
            '''from __future__ import annotations


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())
''',
        )
    },
    "target_functions": ["collapse_whitespace"],
    "issue": """# Whitespace collapser misses repeated tab characters

`collapse_whitespace` should collapse every run of whitespace, including tabs and mixed spaces, into a single space.
""",
    "public_test": '''from task_066_lib.whitespace import collapse_whitespace


def test_single_spaces_unchanged():
    assert collapse_whitespace("hello world") == "hello world"


def test_multiple_spaces_collapsed():
    assert collapse_whitespace("hello   world") == "hello world"


def test_leading_trailing_stripped():
    assert collapse_whitespace("  hello  ") == "hello"
''',
    "hidden_test": '''from task_066_lib.whitespace import collapse_whitespace


def test_tabs_are_collapsed():
    assert collapse_whitespace("hello\\t\\tworld") == "hello world"


def test_mixed_whitespace_collapsed():
    assert collapse_whitespace("one \\t two  \\t  three") == "one two three"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Space runs collapse, but tab-only whitespace is not normalized.",
    "generalization_axis": "Public covers space normalization; hidden covers tab and mixed whitespace.",
}

TASKS["task_067"] = {
    "bug_type": "dict_mutation",
    "package": "task_067_lib",
    "files": {
        "task_067_lib/frequencies.py": (
            '''from __future__ import annotations


def word_freq(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    while words:
        w = words.pop()
        counts[w] = counts.get(w, 0) + 1
    return counts
''',
            '''from __future__ import annotations


def word_freq(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts
''',
        )
    },
    "target_functions": ["word_freq"],
    "issue": """# Word frequency counter destroys the input list

`word_freq` should count occurrences without modifying the caller's list.
""",
    "public_test": '''from task_067_lib.frequencies import word_freq


def test_counts_correctly():
    assert word_freq(["a", "b", "a"]) == {"a": 2, "b": 1}


def test_empty_list():
    assert word_freq([]) == {}
''',
    "hidden_test": '''from task_067_lib.frequencies import word_freq


def test_input_list_is_preserved():
    words = ["x", "y", "x", "z"]
    word_freq(words)
    assert words == ["x", "y", "x", "z"]


def test_input_order_is_preserved():
    words = ["c", "a", "b"]
    word_freq(words)
    assert words == ["c", "a", "b"]
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Counts are correct, but the input list is consumed via pop().",
    "generalization_axis": "Public covers output correctness; hidden covers input non-mutation.",
}

TASKS["task_068"] = {
    "bug_type": "date_boundary",
    "package": "task_068_lib",
    "files": {
        "task_068_lib/months.py": (
            '''from __future__ import annotations


_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def days_in_month(year: int, month: int) -> int:
    return _DAYS[month - 1]
''',
            '''from __future__ import annotations

import calendar


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]
''',
        )
    },
    "target_functions": ["days_in_month"],
    "issue": """# Days-in-month ignores leap years

`days_in_month` should return 29 for February in leap years (every year divisible by 4, except centuries not divisible by 400).
""",
    "public_test": '''from task_068_lib.months import days_in_month


def test_january():
    assert days_in_month(2025, 1) == 31


def test_march():
    assert days_in_month(2025, 3) == 31


def test_april():
    assert days_in_month(2025, 4) == 30
''',
    "hidden_test": '''from task_068_lib.months import days_in_month


def test_february_leap_year():
    assert days_in_month(2024, 2) == 29


def test_february_non_leap_year():
    assert days_in_month(2025, 2) == 28


def test_february_century_non_leap():
    assert days_in_month(1900, 2) == 28


def test_february_century_leap():
    assert days_in_month(2000, 2) == 29
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Non-February months work, but February always returns 28.",
    "generalization_axis": "Public covers non-February months; hidden covers February with leap-year rules.",
}

TASKS["task_069"] = {
    "bug_type": "json_config_parsing",
    "package": "task_069_lib",
    "files": {
        "task_069_lib/config.py": (
            '''from __future__ import annotations

import json


def get_list(config_json: str, key: str) -> list:
    config = json.loads(config_json)
    return config.get(key)
''',
            '''from __future__ import annotations

import json


def get_list(config_json: str, key: str) -> list:
    config = json.loads(config_json)
    return config.get(key, [])
''',
        )
    },
    "target_functions": ["get_list"],
    "issue": """# JSON list accessor returns None for missing keys

`get_list` should return an empty list when the requested key is absent from the configuration, never `None`.
""",
    "public_test": '''from task_069_lib.config import get_list


def test_retrieves_existing_list():
    assert get_list('{"items": [1, 2, 3]}', "items") == [1, 2, 3]


def test_retrieves_empty_list():
    assert get_list('{"items": []}', "items") == []
''',
    "hidden_test": '''from task_069_lib.config import get_list


def test_missing_key_returns_empty_list():
    assert get_list('{"other": true}', "items") == []


def test_empty_object_missing_key():
    assert get_list("{}", "items") == []
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Existing keys work, but missing keys return None instead of [].",
    "generalization_axis": "Public covers key-present cases; hidden covers key-absent default.",
}

TASKS["task_070"] = {
    "bug_type": "cli_argument_propagation",
    "package": "task_070_lib",
    "files": {
        "task_070_lib/transform.py": (
            '''from __future__ import annotations

import argparse


def transform(text: str, mode: str = "upper") -> str:
    if mode == "upper":
        return text.upper()
    elif mode == "lower":
        return text.lower()
    return text


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--mode", default="upper", choices=["upper", "lower"])
    args = parser.parse_args(argv)
    return transform(args.text, mode="upper")
''',
            '''from __future__ import annotations

import argparse


def transform(text: str, mode: str = "upper") -> str:
    if mode == "upper":
        return text.upper()
    elif mode == "lower":
        return text.lower()
    return text


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--mode", default="upper", choices=["upper", "lower"])
    args = parser.parse_args(argv)
    return transform(args.text, mode=args.mode)
''',
        )
    },
    "target_functions": ["main", "transform"],
    "issue": """# CLI mode flag is parsed but hard-coded to upper

The CLI accepts `--mode lower`, but `main` always passes `mode="upper"` to `transform`, ignoring the user's choice.
""",
    "public_test": '''from task_070_lib.transform import main


def test_default_mode_is_upper():
    assert main(["hello"]) == "HELLO"


def test_explicit_upper_mode():
    assert main(["hello", "--mode", "upper"]) == "HELLO"
''',
    "hidden_test": '''from task_070_lib.transform import main


def test_lower_mode_is_honoured():
    assert main(["Hello", "--mode", "lower"]) == "hello"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "The default upper mode works, but --mode lower is ignored.",
    "generalization_axis": "Public covers default and explicit upper; hidden covers the lower path.",
}

# ---- Block 2: 071-080 (medium, P55 bug types) ----

TASKS["task_071"] = {
    "bug_type": "error_handling",
    "package": "task_071_lib",
    "files": {
        "task_071_lib/reader.py": (
            '''from __future__ import annotations


def read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""
''',
            '''from __future__ import annotations


def read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""
''',
        )
    },
    "target_functions": ["read_file"],
    "issue": """# File reader silently swallows permission errors

`read_file` should return an empty string when the file does not exist, but must raise `PermissionError` for unreadable files.
""",
    "public_test": '''import tempfile
from pathlib import Path

from task_071_lib.reader import read_file


def test_reads_existing_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        f.flush()
        result = read_file(f.name)
        Path(f.name).unlink()
    assert result == "hello"


def test_missing_file_returns_empty():
    assert read_file("/tmp/nonexistent_xyz_file.txt") == ""
''',
    "hidden_test": '''import os
import tempfile
from pathlib import Path

from task_071_lib.reader import read_file


def test_permission_error_propagates():
    # Reading a directory as a file should raise, not silently return ""
    with tempfile.TemporaryDirectory() as td:
        try:
            read_file(td)
        except (IsADirectoryError, PermissionError, OSError):
            pass
        else:
            raise AssertionError("expected OSError when reading a directory as a file")
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Normal reads and missing files work, but permissions errors are also silenced.",
    "generalization_axis": "Public covers normal and missing-file cases; hidden covers error propagation.",
}

TASKS["task_072"] = {
    "bug_type": "numeric_edge_case",
    "package": "task_072_lib",
    "files": {
        "task_072_lib/math_utils.py": (
            '''from __future__ import annotations


def safe_percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 1)
''',
            '''from __future__ import annotations


def safe_percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 1)
''',
        )
    },
    "target_functions": ["safe_percentage"],
    "issue": """# safe_percentage mishandles negative denominators

`safe_percentage` should correctly compute percentages when `whole` is negative, returning a signed result.
""",
    "public_test": '''from task_072_lib.math_utils import safe_percentage


def test_positive_whole():
    assert safe_percentage(25, 100) == 25.0


def test_zero_whole():
    assert safe_percentage(25, 0) == 0.0


def test_half():
    assert safe_percentage(1, 2) == 50.0
''',
    "hidden_test": '''from task_072_lib.math_utils import safe_percentage


def test_negative_whole():
    assert safe_percentage(25, -100) == -25.0


def test_negative_part():
    assert safe_percentage(-25, 100) == -25.0
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Wait — this buggy version is actually identical to gold. I need a real bug.",
    "generalization_axis": "Public covers positive cases; hidden covers negative values.",
}

# Fix task_072 — use integer division bug
TASKS["task_072"] = {
    "bug_type": "numeric_edge_case",
    "package": "task_072_lib",
    "files": {
        "task_072_lib/math_utils.py": (
            '''from __future__ import annotations


def safe_percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return (part / whole) * 100
''',
            '''from __future__ import annotations


def safe_percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 2)
''',
        )
    },
    "target_functions": ["safe_percentage"],
    "issue": """# Percentage helper returns unrounded values

`safe_percentage` should round results to 2 decimal places so that `1/3` is reported as `33.33` not `33.333333...`.
""",
    "public_test": '''from task_072_lib.math_utils import safe_percentage


def test_exact_percentage():
    assert safe_percentage(25, 100) == 25.0


def test_zero_whole_is_safe():
    assert safe_percentage(25, 0) == 0.0


def test_fifty_percent():
    assert safe_percentage(1, 2) == 50.0
''',
    "hidden_test": '''from task_072_lib.math_utils import safe_percentage


def test_rounded_to_two_decimals():
    assert safe_percentage(1, 3) == 33.33


def test_rounded_up_at_boundary():
    assert safe_percentage(2, 3) == 66.67
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Exact fractions work, but repeating decimals are not rounded.",
    "generalization_axis": "Public covers fractions that divide evenly; hidden covers repeating decimals.",
}

TASKS["task_073"] = {
    "bug_type": "sorting_filtering",
    "package": "task_073_lib",
    "files": {
        "task_073_lib/ranking.py": (
            '''from __future__ import annotations


def top_by_score(items: list[dict], key: str, n: int) -> list[dict]:
    return sorted(items, key=lambda d: d[key], reverse=True)[:n]
''',
            '''from __future__ import annotations


def top_by_score(items: list[dict], key: str, n: int) -> list[dict]:
    return sorted(items, key=lambda d: d.get(key, 0), reverse=True)[:n]
''',
        )
    },
    "target_functions": ["top_by_score"],
    "issue": """# top_by_score crashes when items are missing the sort key

`top_by_score` should treat missing keys as zero when sorting, instead of raising `KeyError`.
""",
    "public_test": '''from task_073_lib.ranking import top_by_score


def test_picks_top_by_score():
    items = [{"name": "a", "s": 10}, {"name": "b", "s": 30}, {"name": "c", "s": 20}]
    result = top_by_score(items, "s", 2)
    assert len(result) == 2
    assert result[0]["name"] == "b"
    assert result[1]["name"] == "c"


def test_all_have_key():
    items = [{"name": "x", "s": 1}, {"name": "y", "s": 5}]
    result = top_by_score(items, "s", 2)
    assert result[0]["name"] == "y"
''',
    "hidden_test": '''from task_073_lib.ranking import top_by_score


def test_missing_key_treated_as_zero():
    items = [{"name": "a"}, {"name": "b", "s": 5}]
    result = top_by_score(items, "s", 2)
    assert result[0]["name"] == "b"


def test_all_missing_key_sorts_stably():
    items = [{"name": "first"}, {"name": "second"}]
    result = top_by_score(items, "s", 2)
    assert len(result) == 2
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Top scores work, but tie-breaking loses items after the sort cut-off.",
    "generalization_axis": "Public covers distinct scores; hidden covers tie-breaking stability.",
}

TASKS["task_074"] = {
    "bug_type": "service_helper_integration",
    "package": "task_074_lib",
    "files": {
        "task_074_lib/service.py": (
            '''from __future__ import annotations


def fetch_user(users_db: dict[str, dict], user_id: str) -> dict | None:
    return users_db.get(user_id)


def format_name(users_db: dict[str, dict], user_id: str) -> str:
    user = fetch_user(users_db, user_id)
    return f"{user['first']} {user['last']}"
''',
            '''from __future__ import annotations


def fetch_user(users_db: dict[str, dict], user_id: str) -> dict | None:
    return users_db.get(user_id)


def format_name(users_db: dict[str, dict], user_id: str) -> str:
    user = fetch_user(users_db, user_id)
    if user is None:
        return "Unknown"
    return f"{user['first']} {user['last']}"
''',
        )
    },
    "target_functions": ["fetch_user", "format_name"],
    "issue": """# format_name crashes on missing users

`format_name` should return `"Unknown"` when the user does not exist, instead of crashing with an attribute error.
""",
    "public_test": '''from task_074_lib.service import format_name


def test_formats_existing_user():
    db = {"u1": {"first": "Ada", "last": "Lovelace"}}
    assert format_name(db, "u1") == "Ada Lovelace"


def test_formats_another_user():
    db = {"a": {"first": "Alan", "last": "Turing"}}
    assert format_name(db, "a") == "Alan Turing"
''',
    "hidden_test": '''from task_074_lib.service import format_name


def test_missing_user_returns_unknown():
    db = {"u1": {"first": "Ada", "last": "Lovelace"}}
    assert format_name(db, "u2") == "Unknown"


def test_empty_db_returns_unknown():
    assert format_name({}, "anyone") == "Unknown"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Existing users work, but missing users cause a TypeError crash.",
    "generalization_axis": "Public covers found users; hidden covers null/missing user handling.",
}

TASKS["task_075"] = {
    "bug_type": "case_insensitive_handling",
    "package": "task_075_lib",
    "files": {
        "task_075_lib/lookup.py": (
            '''from __future__ import annotations


def case_insensitive_get(mapping: dict[str, str], key: str) -> str | None:
    return mapping.get(key)
''',
            '''from __future__ import annotations


def case_insensitive_get(mapping: dict[str, str], key: str) -> str | None:
    lowered = {k.lower(): v for k, v in mapping.items()}
    return lowered.get(key.lower())
''',
        )
    },
    "target_functions": ["case_insensitive_get"],
    "issue": """# Dict lookup is case-sensitive instead of case-insensitive

`case_insensitive_get` should find values regardless of key casing, so `"Host"` and `"host"` retrieve the same entry.
""",
    "public_test": '''from task_075_lib.lookup import case_insensitive_get


def test_exact_match_works():
    headers = {"host": "localhost", "port": "8080"}
    assert case_insensitive_get(headers, "host") == "localhost"


def test_returns_none_for_missing():
    headers = {"host": "localhost"}
    assert case_insensitive_get(headers, "missing") is None
''',
    "hidden_test": '''from task_075_lib.lookup import case_insensitive_get


def test_case_insensitive_match():
    headers = {"Host": "localhost"}
    assert case_insensitive_get(headers, "host") == "localhost"


def test_mixed_case_both_sides():
    headers = {"Content-Type": "application/json"}
    assert case_insensitive_get(headers, "content-type") == "application/json"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Exact string match works, but case-insensitive lookup is not performed.",
    "generalization_axis": "Public covers exact match; hidden covers case-insensitive matching.",
}

TASKS["task_076"] = {
    "bug_type": "multi_file_integration",
    "package": "task_076_lib",
    "files": {
        "task_076_lib/__init__.py": ("", ""),
        "task_076_lib/validator.py": (
            '''from __future__ import annotations


def is_positive(n: int) -> bool:
    return n > 0
''',
            '''from __future__ import annotations


def is_positive(n: int) -> bool:
    return n > 0


def is_even(n: int) -> bool:
    return n % 2 == 0
''',
        ),
        "task_076_lib/filtering.py": (
            '''from __future__ import annotations

from task_076_lib.validator import is_even


def filter_valid(numbers: list[int]) -> list[int]:
    return [n for n in numbers if is_even(n)]
''',
            '''from __future__ import annotations

from task_076_lib.validator import is_even


def filter_valid(numbers: list[int]) -> list[int]:
    return [n for n in numbers if is_even(n)]
''',
        ),
    },
    "target_functions": ["is_positive", "is_even", "filter_valid"],
    "issue": """# filter_valid imports a function that does not exist

`filter_valid` imports `is_even` from the validator module, but `is_even` is not defined there. The fix should add `is_even` to the validator.
""",
    "public_test": '''from task_076_lib.validator import is_positive


def test_is_positive_true():
    assert is_positive(5) is True


def test_is_positive_false():
    assert is_positive(-1) is False
    assert is_positive(0) is False
''',
    "hidden_test": '''from task_076_lib.filtering import filter_valid


def test_filter_keeps_even_numbers():
    assert filter_valid([1, 2, 3, 4, 5, 6]) == [2, 4, 6]


def test_filter_returns_empty_when_no_evens():
    assert filter_valid([1, 3, 5]) == []
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "The validator module passes its own tests, but the filtering module fails at import time.",
    "generalization_axis": "Public covers the validator module; hidden covers cross-module integration.",
}

TASKS["task_077"] = {
    "bug_type": "stateful_side_effect",
    "package": "task_077_lib",
    "files": {
        "task_077_lib/stack.py": (
            '''from __future__ import annotations


class IntStack:
    def __init__(self) -> None:
        self._items: list[int] = []
        self._popped: list[int] = []

    def push(self, value: int) -> None:
        self._items.append(value)

    def pop(self) -> int | None:
        if not self._items:
            return None
        value = self._items.pop()
        self._popped.append(value)
        return value

    def size(self) -> int:
        return len(self._items)

    def popped_count(self) -> int:
        return len(self._popped)

    def clear(self) -> None:
        self._items.clear()
''',
            '''from __future__ import annotations


class IntStack:
    def __init__(self) -> None:
        self._items: list[int] = []
        self._popped: list[int] = []

    def push(self, value: int) -> None:
        self._items.append(value)

    def pop(self) -> int | None:
        if not self._items:
            return None
        value = self._items.pop()
        self._popped.append(value)
        return value

    def size(self) -> int:
        return len(self._items)

    def popped_count(self) -> int:
        return len(self._popped)

    def clear(self) -> None:
        self._items.clear()
        self._popped.clear()
''',
        )
    },
    "target_functions": ["IntStack.push", "IntStack.pop", "IntStack.clear", "IntStack.popped_count"],
    "issue": """# IntStack.clear does not reset pop history

`IntStack.clear` should reset the stack to its initial state, including clearing the internal pop-history list so `popped_count()` returns 0 after clear.
""",
    "public_test": '''from task_077_lib.stack import IntStack


def test_push_and_pop():
    s = IntStack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1


def test_size_after_operations():
    s = IntStack()
    s.push(10)
    s.push(20)
    s.pop()
    assert s.size() == 1


def test_clear_empties_stack():
    s = IntStack()
    s.push(1)
    s.push(2)
    s.clear()
    assert s.size() == 0
    assert s.pop() is None
''',
    "hidden_test": '''from task_077_lib.stack import IntStack


def test_clear_resets_popped_count():
    s = IntStack()
    s.push(10)
    s.push(20)
    s.pop()
    assert s.popped_count() == 1
    s.clear()
    assert s.popped_count() == 0


def test_fresh_stack_has_zero_popped_count():
    s = IntStack()
    assert s.popped_count() == 0
    s.push(1)
    s.pop()
    assert s.popped_count() == 1
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Push/pop/clear work for the main items list, but popped_count is not reset by clear().",
    "generalization_axis": "Public covers basic stack operations; hidden covers popped_count reset.",
}

TASKS["task_078"] = {
    "bug_type": "idempotency",
    "package": "task_078_lib",
    "files": {
        "task_078_lib/init_once.py": (
            '''from __future__ import annotations

from typing import Any

_INITIALIZED: dict[str, Any] = {}


def initialize(key: str, factory: Any) -> Any:
    if key not in _INITIALIZED:
        _INITIALIZED[key] = factory() if callable(factory) else factory
    return _INITIALIZED[key]
''',
            '''from __future__ import annotations

from typing import Any

_INITIALIZED: dict[str, Any] = {}


def initialize(key: str, factory: Any) -> Any:
    if key not in _INITIALIZED:
        _INITIALIZED[key] = factory() if callable(factory) else factory
    return _INITIALIZED[key]


def reset_initialized(key: str | None = None) -> None:
    if key is None:
        _INITIALIZED.clear()
    else:
        _INITIALIZED.pop(key, None)
''',
        )
    },
    "target_functions": ["initialize"],
    "issue": """# initialize cannot be reset for testing

`initialize` correctly creates each value only once, but there is no way to reset the global state between tests without restarting the process. A `reset_initialized` function is needed.
""",
    "public_test": '''from task_078_lib.init_once import initialize


def test_returns_same_value_on_repeated_call():
    a = initialize("test_key", list)
    b = initialize("test_key", list)
    assert a is b


def test_different_keys_are_independent():
    a = initialize("key_a", list)
    b = initialize("key_b", list)
    assert a is not b
''',
    "hidden_test": '''from task_078_lib.init_once import initialize, reset_initialized


def test_reset_allows_reinitialization():
    a = initialize("resettable", list)
    reset_initialized("resettable")
    b = initialize("resettable", list)
    assert a is not b


def test_reset_all_clears_everything():
    a = initialize("k1", list)
    b = initialize("k2", list)
    reset_initialized()
    c = initialize("k1", list)
    assert a is not c
    assert initialize("k2", list) is not b
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Initialization works, but the hidden test can only pass if reset exists.",
    "generalization_axis": "Public covers basic initialize behaviour; hidden covers reset for idempotency testing.",
}

TASKS["task_079"] = {
    "bug_type": "validation_logic",
    "package": "task_079_lib",
    "files": {
        "task_079_lib/email_check.py": (
            '''from __future__ import annotations


def is_valid_email(address: str) -> bool:
    return "@" in address and "." in address
''',
            '''from __future__ import annotations


def is_valid_email(address: str) -> bool:
    at_pos = address.find("@")
    if at_pos <= 0:
        return False
    dot_pos = address.rfind(".")
    return dot_pos > at_pos + 1 and dot_pos < len(address) - 1
''',
        )
    },
    "target_functions": ["is_valid_email"],
    "issue": """# Email validator is too lenient

`is_valid_email` should require `@` to not be the first character, and a dot must appear after `@` but before the end.
""",
    "public_test": '''from task_079_lib.email_check import is_valid_email


def test_valid_email():
    assert is_valid_email("alice@example.com") is True


def test_no_at_sign():
    assert is_valid_email("aliceexample.com") is False


def test_no_dot():
    assert is_valid_email("alice@example") is False
''',
    "hidden_test": '''from task_079_lib.email_check import is_valid_email


def test_at_sign_at_start_is_invalid():
    assert is_valid_email("@example.com") is False


def test_dot_before_at_is_rejected():
    assert is_valid_email("alice.smith@examplecom") is False


def test_dot_at_end_is_invalid():
    assert is_valid_email("alice@example.") is False


def test_dot_immediately_after_at_is_invalid():
    assert is_valid_email("alice@.com") is False
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Simple valid/invalid checks pass, but edge positions like leading @ or trailing dot are accepted.",
    "generalization_axis": "Public covers presence of @ and .; hidden covers positional constraints.",
}

TASKS["task_080"] = {
    "bug_type": "config_merge",
    "package": "task_080_lib",
    "files": {
        "task_080_lib/merge.py": (
            '''from __future__ import annotations


def merge_lists(a: list, b: list) -> list:
    return a + b
''',
            '''from __future__ import annotations


def merge_lists(a: list, b: list) -> list:
    seen = set()
    result = []
    for item in a + b:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
''',
        )
    },
    "target_functions": ["merge_lists"],
    "issue": """# List merger duplicates overlapping entries

`merge_lists` should concatenate two lists while preserving order and removing duplicates so that each value appears only once.
""",
    "public_test": '''from task_080_lib.merge import merge_lists


def test_disjoint_lists():
    assert merge_lists([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_empty_second():
    assert merge_lists([1, 2], []) == [1, 2]


def test_both_empty():
    assert merge_lists([], []) == []
''',
    "hidden_test": '''from task_080_lib.merge import merge_lists


def test_overlapping_lists_deduplicated():
    assert merge_lists([1, 2, 3], [2, 3, 4]) == [1, 2, 3, 4]


def test_first_already_contains_all():
    assert merge_lists(["a", "b", "c"], ["b"]) == ["a", "b", "c"]


def test_order_preserved_with_dedup():
    assert merge_lists([3, 1], [2, 1, 4]) == [3, 1, 2, 4]
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Simple concatenation works, but overlapping values appear twice.",
    "generalization_axis": "Public covers disjoint lists; hidden covers deduplication of overlaps.",
}

# ---- Block 3: 081-090 (hard, P50 bug types) ----

TASKS["task_081"] = {
    "bug_type": "parsing_edge_case",
    "package": "task_081_lib",
    "files": {
        "task_081_lib/ini_reader.py": (
            '''from __future__ import annotations


def parse_ini_section(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.strip().split("\\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result
''',
            '''from __future__ import annotations


def parse_ini_section(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.strip().split("\\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip(\'"\')
    return result
''',
        )
    },
    "target_functions": ["parse_ini_section"],
    "issue": """# INI parser does not handle semicolon comments or quoted values

`parse_ini_section` should skip lines starting with `;` (semicolon comments) and strip surrounding double-quotes from values.
""",
    "public_test": '''from task_081_lib.ini_reader import parse_ini_section


def test_parses_simple_keys():
    result = parse_ini_section("host=localhost\\nport=5432")
    assert result == {"host": "localhost", "port": "5432"}


def test_skips_hash_comments():
    result = parse_ini_section("# config file\\nkey=value")
    assert result == {"key": "value"}
''',
    "hidden_test": '''from task_081_lib.ini_reader import parse_ini_section


def test_skips_semicolon_comments():
    result = parse_ini_section("; this is a comment\\nname=alice")
    assert result == {"name": "alice"}


def test_strips_double_quotes_from_value():
    result = parse_ini_section('path="/usr/local/bin"')
    assert result == {"path": "/usr/local/bin"}


def test_empty_value_after_quotes():
    result = parse_ini_section('empty=""')
    assert result == {"empty": ""}
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Basic parsing and #-comments work; ;-comments are treated as keys and quotes are kept.",
    "generalization_axis": "Public covers simple parsing; hidden covers semicolon comments and value quoting.",
}

TASKS["task_082"] = {
    "bug_type": "path_handling",
    "package": "task_082_lib",
    "files": {
        "task_082_lib/extension.py": (
            '''from __future__ import annotations


def split_extension(path: str) -> tuple[str, str]:
    if "." in path:
        base, ext = path.rsplit(".", 1)
        return base, "." + ext
    return path, ""
''',
            '''from __future__ import annotations

_KNOWN_COMPOUND = {".tar.gz", ".tar.bz2", ".tar.xz"}


def split_extension(path: str) -> tuple[str, str]:
    for comp in sorted(_KNOWN_COMPOUND, key=len, reverse=True):
        if path.endswith(comp):
            return path[:-len(comp)], comp
    if "." in path:
        base, ext = path.rsplit(".", 1)
        return base, "." + ext
    return path, ""
''',
        )
    },
    "target_functions": ["split_extension"],
    "issue": """# Extension splitter does not recognise compound extensions

`split_extension` should detect compound extensions such as `.tar.gz` and return them as a single extension.
""",
    "public_test": '''from task_082_lib.extension import split_extension


def test_simple_extension():
    assert split_extension("readme.txt") == ("readme", ".txt")


def test_no_extension():
    assert split_extension("Makefile") == ("Makefile", "")


def test_multiple_dots_returns_last_ext():
    assert split_extension("image.png.jpg") == ("image.png", ".jpg")
''',
    "hidden_test": '''from task_082_lib.extension import split_extension


def test_known_compound_tar_gz():
    assert split_extension("backup.tar.gz") == ("backup", ".tar.gz")


def test_known_compound_tar_bz2():
    assert split_extension("data.tar.bz2") == ("data", ".tar.bz2")


def test_unknown_double_is_split_normally():
    assert split_extension("image.png.jpg") == ("image.png", ".jpg")
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Simple extensions work, but compound extensions like .tar.gz are split as .gz.",
    "generalization_axis": "Public covers simple extensions; hidden covers compound-extension detection.",
}

TASKS["task_083"] = {
    "bug_type": "cache_key",
    "package": "task_083_lib",
    "files": {
        "task_083_lib/hashing.py": (
            '''from __future__ import annotations

import hashlib


def hash_args(*args: object) -> str:
    raw = ":".join(str(a) for a in args)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
''',
            '''from __future__ import annotations

import hashlib


def hash_args(*args: object) -> str:
    parts = []
    for a in args:
        if isinstance(a, (list, tuple)):
            parts.append("[" + ",".join(str(x) for x in a) + "]")
        elif isinstance(a, dict):
            parts.append("{" + ",".join(f"{k}={v}" for k, v in sorted(a.items())) + "}")
        else:
            parts.append(str(a))
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
''',
        )
    },
    "target_functions": ["hash_args"],
    "issue": """# Argument hasher is not stable for collections

`hash_args` should produce the same hash for identical arguments, including when lists, tuples, and dicts are used. Dict ordering should not affect the result.
""",
    "public_test": '''from task_083_lib.hashing import hash_args


def test_same_args_same_hash():
    assert hash_args(1, 2, 3) == hash_args(1, 2, 3)


def test_different_args_different_hash():
    assert hash_args(1, 2) != hash_args(1, 2, 3)
''',
    "hidden_test": '''from task_083_lib.hashing import hash_args


def test_dict_order_does_not_matter():
    a = hash_args({"a": 1, "b": 2})
    b = hash_args({"b": 2, "a": 1})
    assert a == b


def test_list_with_same_elements():
    assert hash_args([1, 2, 3]) == hash_args([1, 2, 3])


def test_tuple_and_list_of_same_values_same_hash():
    assert hash_args([1, 2]) == hash_args((1, 2))
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Scalar arguments hash consistently, but collections use unstable repr.",
    "generalization_axis": "Public covers scalar identity; hidden covers collection stability.",
}

TASKS["task_084"] = {
    "bug_type": "optional_default_args",
    "package": "task_084_lib",
    "files": {
        "task_084_lib/formatting.py": (
            '''from __future__ import annotations

from typing import Any


def format_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    columns.sort()
    lines = ["\\t".join(columns)]
    for row in rows:
        lines.append("\\t".join(str(row.get(c, "")) for c in columns))
    return "\\n".join(lines)
''',
            '''from __future__ import annotations

from typing import Any


def format_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if columns is not None:
        cols = sorted(columns)
    else:
        cols = list(rows[0].keys()) if rows else []
    lines = ["\\t".join(cols)]
    for row in rows:
        lines.append("\\t".join(str(row.get(c, "")) for c in cols))
    return "\\n".join(lines)
''',
        )
    },
    "target_functions": ["format_table"],
    "issue": """# Table formatter mutates the caller's column list

`format_table` should not modify the list passed as `columns`. When the user passes an explicit column list, it should be safe to reuse.
""",
    "public_test": '''from task_084_lib.formatting import format_table


def test_formats_with_default_columns():
    rows = [{"name": "Ada", "age": 28}]
    result = format_table(rows)
    assert "name" in result
    assert "age" in result
    assert "Ada" in result


def test_formats_with_explicit_columns():
    rows = [{"name": "Ada", "age": 28, "city": "London"}]
    result = format_table(rows, columns=["name", "age"])
    lines = result.split("\\n")
    assert len(lines) == 2


def test_empty_rows():
    assert format_table([]) == ""
''',
    "hidden_test": '''from task_084_lib.formatting import format_table


def test_input_columns_not_mutated():
    rows = [{"a": 1, "b": 2, "c": 3}]
    cols = ["b", "a"]
    format_table(rows, columns=cols)
    assert cols == ["b", "a"]


def test_input_columns_order_preserved():
    rows = [{"x": 10, "y": 20}]
    cols = ["y", "x"]
    format_table(rows, columns=cols)
    assert cols == ["y", "x"]
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Table formatting works, but the columns argument is aliased and mutated.",
    "generalization_axis": "Public covers output correctness; hidden covers input non-mutation.",
}

TASKS["task_085"] = {
    "bug_type": "boundary_condition",
    "package": "task_085_lib",
    "files": {
        "task_085_lib/wrap.py": (
            '''from __future__ import annotations


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
''',
            '''from __future__ import annotations


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        while len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:width])
            word = word[width:]
        if current and len(current) + len(word) + 1 <= width:
            current = current + " " + word
        elif current:
            lines.append(current)
            current = word
        else:
            current = word
    if current:
        lines.append(current)
    return lines
''',
        )
    },
    "target_functions": ["wrap_text"],
    "issue": """# Text wrapper drops words longer than the wrap width

`wrap_text` should break a word that is longer than `width` across multiple lines instead of silently dropping it.
""",
    "public_test": '''from task_085_lib.wrap import wrap_text


def test_short_words_fit():
    assert wrap_text("hello world", 20) == ["hello world"]


def test_wraps_at_width():
    result = wrap_text("hello world foo", 10)
    assert len(result) == 2
    assert result[0] == "hello"
    assert result[1] == "world foo"


def test_empty_text():
    assert wrap_text("", 10) == []
''',
    "hidden_test": '''from task_085_lib.wrap import wrap_text


def test_long_word_is_split():
    result = wrap_text("hello supercalifragilistic world", 10)
    assert "supercalif" in result
    assert "ragilistic" in result


def test_long_word_preserves_other_words():
    result = wrap_text("a verylongword b", 5)
    assert result[0] == "a"
    assert result[1] == "veryl"
    assert "b" in result[-1]
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Normal-width words wrap correctly, but a word exceeding the width is silently skipped.",
    "generalization_axis": "Public covers standard wrapping; hidden covers overflow-word splitting.",
}

TASKS["task_086"] = {
    "bug_type": "string_normalization",
    "package": "task_086_lib",
    "files": {
        "task_086_lib/unicode_utils.py": (
            '''from __future__ import annotations


def strip_accents(text: str) -> str:
    replacements = {"\\u00e9": "e", "\\u00fc": "u", "\\u00e0": "a"}
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text
''',
            '''from __future__ import annotations

import unicodedata


def strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    result = "".join(c for c in nfd if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", result)
''',
        )
    },
    "target_functions": ["strip_accents"],
    "issue": """# Accent stripper misses many diacritics

`strip_accents` should remove all accent marks using proper Unicode decomposition, not a fixed set of replacements.
""",
    "public_test": '''from task_086_lib.unicode_utils import strip_accents


def test_plain_ascii_unchanged():
    assert strip_accents("hello") == "hello"


def test_accented_e_removed():
    assert strip_accents("caf\\u00e9") == "cafe"
''',
    "hidden_test": '''from task_086_lib.unicode_utils import strip_accents


def test_tilde_is_removed():
    assert strip_accents("se\\u00f1or") == "senor"


def test_circumflex_is_removed():
    assert strip_accents("\\u00eatre") == "etre"


def test_multiple_accents_in_one_word():
    assert strip_accents("\\u00e1\\u00e9\\u00ed\\u00f3\\u00fa") == "aeiou"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Accents are removed, but the output is in decomposed form instead of composed NFC.",
    "generalization_axis": "Public covers basic stripping; hidden covers normalization form.",
}

TASKS["task_087"] = {
    "bug_type": "dict_mutation",
    "package": "task_087_lib",
    "files": {
        "task_087_lib/defaults.py": (
            '''from __future__ import annotations

from typing import Any


def apply_defaults(target: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    for key, value in defaults.items():
        if key not in target:
            target[key] = value
    return target
''',
            '''from __future__ import annotations

from typing import Any


def apply_defaults(target: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    result = dict(target)
    for key, value in defaults.items():
        if key not in result:
            result[key] = value
    return result
''',
        )
    },
    "target_functions": ["apply_defaults"],
    "issue": """# apply_defaults mutates the caller's dictionary

`apply_defaults` should return a new dictionary with defaults filled in, but must leave the original `target` unchanged.
""",
    "public_test": '''from task_087_lib.defaults import apply_defaults


def test_fills_missing_keys():
    result = apply_defaults({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}


def test_keeps_existing_keys():
    result = apply_defaults({"a": 1}, {"a": 99, "b": 2})
    assert result == {"a": 1, "b": 2}


def test_empty_defaults_is_noop():
    assert apply_defaults({"x": 1}, {}) == {"x": 1}
''',
    "hidden_test": '''from task_087_lib.defaults import apply_defaults


def test_original_dict_not_mutated():
    original = {"host": "localhost"}
    apply_defaults(original, {"port": 5432})
    assert original == {"host": "localhost"}


def test_original_dict_not_mutated_when_key_exists():
    original = {"host": "localhost"}
    apply_defaults(original, {"host": "default"})
    assert original == {"host": "localhost"}
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Defaults are applied, but the original dict is modified in place.",
    "generalization_axis": "Public covers output correctness; hidden covers non-mutation of input.",
}

TASKS["task_088"] = {
    "bug_type": "date_boundary",
    "package": "task_088_lib",
    "files": {
        "task_088_lib/dates.py": (
            '''from __future__ import annotations

from datetime import date, timedelta


def weeks_between(start: date, end: date) -> int:
    return (end - start).days // 7
''',
            '''from __future__ import annotations

from datetime import date, timedelta


def weeks_between(start: date, end: date) -> int:
    delta = abs((end - start).days)
    return delta // 7
''',
        )
    },
    "target_functions": ["weeks_between"],
    "issue": """# weeks_between mishandles reversed date ranges

`weeks_between` should return the absolute number of whole weeks between two dates, regardless of which date is earlier.
""",
    "public_test": '''from datetime import date

from task_088_lib.dates import weeks_between


def test_positive_range():
    assert weeks_between(date(2026, 1, 1), date(2026, 1, 22)) == 3


def test_same_date():
    assert weeks_between(date(2026, 6, 1), date(2026, 6, 1)) == 0


def test_one_week():
    assert weeks_between(date(2026, 1, 1), date(2026, 1, 8)) == 1
''',
    "hidden_test": '''from datetime import date

from task_088_lib.dates import weeks_between


def test_reversed_range_returns_positive():
    assert weeks_between(date(2026, 1, 22), date(2026, 1, 1)) == 3


def test_reversed_partial_week():
    assert weeks_between(date(2026, 1, 10), date(2026, 1, 1)) == 1
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Forward ranges work, but reversed ranges produce negative results.",
    "generalization_axis": "Public covers forward date ranges; hidden covers reversed-order ranges.",
}

TASKS["task_089"] = {
    "bug_type": "json_config_parsing",
    "package": "task_089_lib",
    "files": {
        "task_089_lib/settings.py": (
            '''from __future__ import annotations

import json


def get_nested(config_json: str, path: str) -> object:
    data = json.loads(config_json)
    for key in path.split("."):
        data = data[key]
    return data
''',
            '''from __future__ import annotations

import json


def get_nested(config_json: str, path: str) -> object:
    data = json.loads(config_json)
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        else:
            raise KeyError(f"cannot descend into non-dict at {key!r}")
        if data is None:
            return None
    return data
''',
        )
    },
    "target_functions": ["get_nested"],
    "issue": """# Nested JSON accessor crashes on missing intermediate keys

`get_nested` should return `None` when any segment of the dotted path is absent, instead of raising `KeyError`.
""",
    "public_test": '''from task_089_lib.settings import get_nested


def test_single_level():
    assert get_nested('{"host": "localhost"}', "host") == "localhost"


def test_nested_path():
    result = get_nested('{"db": {"host": "localhost"}}', "db.host")
    assert result == "localhost"


def test_numeric_value():
    assert get_nested('{"port": 5432}', "port") == 5432
''',
    "hidden_test": '''from task_089_lib.settings import get_nested


def test_missing_top_level_key_returns_none():
    assert get_nested('{"a": 1}', "b") is None


def test_missing_nested_key_returns_none():
    assert get_nested('{"db": {"host": "localhost"}}', "db.port") is None


def test_deeply_missing_key_returns_none():
    assert get_nested('{"a": {"b": 1}}', "a.c.d") is None
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Existing paths work, but missing keys raise KeyError instead of returning None.",
    "generalization_axis": "Public covers existing paths; hidden covers missing-key fallback.",
}

TASKS["task_090"] = {
    "bug_type": "cli_argument_propagation",
    "package": "task_090_lib",
    "files": {
        "task_090_lib/repeat.py": (
            '''from __future__ import annotations

import argparse


def repeat(text: str, count: int = 1, sep: str = " ") -> str:
    return sep.join([text] * count)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--sep", default=" ")
    args = parser.parse_args(argv)
    return repeat(args.text, count=1, sep=args.sep)
''',
            '''from __future__ import annotations

import argparse


def repeat(text: str, count: int = 1, sep: str = " ") -> str:
    return sep.join([text] * count)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--sep", default=" ")
    args = parser.parse_args(argv)
    return repeat(args.text, count=args.count, sep=args.sep)
''',
        )
    },
    "target_functions": ["main", "repeat"],
    "issue": """# CLI repeat command ignores --count

The CLI accepts `--count N`, but `main` always passes `count=1` to `repeat`, so the text is never actually repeated.
""",
    "public_test": '''from task_090_lib.repeat import main


def test_single_repetition():
    assert main(["hello"]) == "hello"


def test_count_one_explicit():
    assert main(["hello", "--count", "1"]) == "hello"


def test_custom_separator():
    assert main(["a", "--sep", ","]) == "a"
''',
    "hidden_test": '''from task_090_lib.repeat import main


def test_repeat_three_times():
    assert main(["x", "--count", "3"]) == "x x x"


def test_repeat_with_custom_sep_and_count():
    assert main(["y", "--count", "2", "--sep", "-"]) == "y-y"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Default count=1 works, but --count is parsed and then ignored.",
    "generalization_axis": "Public covers default count; hidden covers explicit count propagation.",
}

# ---- Block 4: 091-100 (hard, P55 bug types) ----

TASKS["task_091"] = {
    "bug_type": "error_handling",
    "package": "task_091_lib",
    "files": {
        "task_091_lib/gateway.py": (
            '''from __future__ import annotations


def fetch_with_timeout(url: str, timeout: float = 5.0) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode()
    except Exception:
        return ""
''',
            '''from __future__ import annotations


def fetch_with_timeout(url: str, timeout: float = 5.0) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode()
    except (OSError, ValueError):
        return ""
''',
        )
    },
    "target_functions": ["fetch_with_timeout"],
    "issue": """# HTTP fetch helper swallows programming errors

`fetch_with_timeout` should catch network and URL errors gracefully, but must not suppress `TypeError` or `AttributeError` caused by incorrect arguments.
""",
    "public_test": '''from task_091_lib.gateway import fetch_with_timeout


def test_invalid_url_returns_empty():
    result = fetch_with_timeout("not-a-valid-url")
    assert result == ""


def test_nonexistent_host_returns_empty():
    result = fetch_with_timeout("http://192.0.2.1.nonexistent.test/", timeout=0.1)
    assert result == ""
''',
    "hidden_test": '''from task_091_lib.gateway import fetch_with_timeout


def test_none_url_is_not_silenced():
    try:
        fetch_with_timeout(None)  # type: ignore
    except Exception:
        pass
    else:
        raise AssertionError("expected exception for None url")


def test_invalid_timeout_type_raises():
    try:
        fetch_with_timeout("http://example.com", timeout="fast")  # type: ignore
    except Exception:
        pass
    else:
        raise AssertionError("expected exception for string timeout")
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Bad URLs are handled, but type errors from None url are also silenced.",
    "generalization_axis": "Public covers network errors; hidden covers type-error propagation.",
}

TASKS["task_092"] = {
    "bug_type": "numeric_edge_case",
    "package": "task_092_lib",
    "files": {
        "task_092_lib/bounds.py": (
            '''from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value
''',
            '''from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    if high < low:
        raise ValueError(f"low ({low}) must not exceed high ({high})")
    if value < low:
        return low
    if value > high:
        return high
    return value
''',
        )
    },
    "target_functions": ["clamp"],
    "issue": """# Clamp function silently accepts swapped bounds

`clamp` should raise `ValueError` when `low > high` so callers do not silently get an incorrectly constrained value when the bounds are specified in reverse order.
""",
    "public_test": '''from task_092_lib.bounds import clamp


def test_value_within_range():
    assert clamp(5, 0, 10) == 5


def test_value_below_range():
    assert clamp(-5, 0, 10) == 0


def test_value_above_range():
    assert clamp(15, 0, 10) == 10


def test_value_at_lower_boundary():
    assert clamp(0, 0, 10) == 0
''',
    "hidden_test": '''from task_092_lib.bounds import clamp


def test_swapped_bounds_raise_value_error():
    try:
        clamp(5, 10, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for swapped bounds")


def test_equal_bounds_are_valid():
    assert clamp(7, 5, 5) == 5
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Normal clamping works, but swapped bounds silently return incorrect results.",
    "generalization_axis": "Public covers normal clamping; hidden covers bound validation.",
}

TASKS["task_093"] = {
    "bug_type": "sorting_filtering",
    "package": "task_093_lib",
    "files": {
        "task_093_lib/matchers.py": (
            '''from __future__ import annotations


def filter_by_prefix(items: list[str], prefix: str) -> list[str]:
    return [item for item in items if item.startswith(prefix)]
''',
            '''from __future__ import annotations


def filter_by_prefix(items: list[str], prefix: str, case_sensitive: bool = True) -> list[str]:
    if case_sensitive:
        return [item for item in items if item.startswith(prefix)]
    lower_pfx = prefix.lower()
    return [item for item in items if item.lower().startswith(lower_pfx)]
''',
        )
    },
    "target_functions": ["filter_by_prefix"],
    "issue": """# Prefix filter is always case-sensitive

`filter_by_prefix` should support a `case_sensitive` parameter so callers can request case-insensitive matching.
""",
    "public_test": '''from task_093_lib.matchers import filter_by_prefix


def test_case_sensitive_match():
    result = filter_by_prefix(["apple", "Apply", "banana"], "app")
    assert result == ["apple"]


def test_empty_list():
    assert filter_by_prefix([], "x") == []


def test_no_matches():
    assert filter_by_prefix(["abc", "def"], "xyz") == []
''',
    "hidden_test": '''from task_093_lib.matchers import filter_by_prefix


def test_case_insensitive_match():
    result = filter_by_prefix(["Apple", "apply", "banana"], "app", case_sensitive=False)
    assert result == ["Apple", "apply"]


def test_case_insensitive_no_match():
    result = filter_by_prefix(["banana", "cherry"], "app", case_sensitive=False)
    assert result == []
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Case-sensitive filtering works, but case-insensitive mode is not implemented.",
    "generalization_axis": "Public covers case-sensitive filtering; hidden covers case-insensitive mode.",
}

TASKS["task_094"] = {
    "bug_type": "service_helper_integration",
    "package": "task_094_lib",
    "files": {
        "task_094_lib/orchestrator.py": (
            '''from __future__ import annotations


def enrich(record: dict, lookup: dict[str, str]) -> dict:
    result = dict(record)
    result["full_name"] = lookup.get(record.get("id", ""), "Unknown")
    return result
''',
            '''from __future__ import annotations


def enrich(record: dict, lookup: dict[str, str], id_key: str = "id") -> dict:
    result = dict(record)
    result["full_name"] = lookup.get(record.get(id_key, ""), "Unknown")
    return result
''',
        )
    },
    "target_functions": ["enrich"],
    "issue": """# Enrich function hard-codes the ID key

`enrich` should accept an optional `id_key` parameter so callers can specify which field holds the lookup identifier (e.g., `"user_id"` instead of `"id"`).
""",
    "public_test": '''from task_094_lib.orchestrator import enrich


def test_enriches_with_default_id():
    lookup = {"u1": "Alice", "u2": "Bob"}
    record = {"id": "u1", "score": 100}
    result = enrich(record, lookup)
    assert result["full_name"] == "Alice"
    assert result["score"] == 100


def test_missing_id_returns_unknown():
    lookup = {"u1": "Alice"}
    record = {"id": "u99", "score": 50}
    result = enrich(record, lookup)
    assert result["full_name"] == "Unknown"
''',
    "hidden_test": '''from task_094_lib.orchestrator import enrich


def test_enriches_with_custom_id_key():
    lookup = {"u1": "Alice", "u2": "Bob"}
    record = {"user_id": "u2", "score": 90}
    result = enrich(record, lookup, id_key="user_id")
    assert result["full_name"] == "Bob"


def test_custom_id_key_missing():
    lookup = {"u1": "Alice"}
    record = {"uid": "u99", "score": 10}
    result = enrich(record, lookup, id_key="uid")
    assert result["full_name"] == "Unknown"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Default 'id' key works, but custom id_key is not supported (signature mismatch).",
    "generalization_axis": "Public covers default id key; hidden covers custom id-key parameter.",
}

TASKS["task_095"] = {
    "bug_type": "case_insensitive_handling",
    "package": "task_095_lib",
    "files": {
        "task_095_lib/commands.py": (
            '''from __future__ import annotations


_COMMANDS: dict[str, str] = {}


def register(name: str, handler: str) -> None:
    _COMMANDS[name] = handler


def dispatch(name: str) -> str | None:
    return _COMMANDS.get(name)
''',
            '''from __future__ import annotations


_COMMANDS: dict[str, str] = {}


def register(name: str, handler: str) -> None:
    _COMMANDS[name.lower()] = handler


def dispatch(name: str) -> str | None:
    return _COMMANDS.get(name.lower())
''',
        )
    },
    "target_functions": ["register", "dispatch"],
    "issue": """# Command dispatcher is case-sensitive

`dispatch` should find commands regardless of the casing used at registration or invocation, so `"HELP"` and `"help"` resolve to the same handler.
""",
    "public_test": '''from task_095_lib.commands import register, dispatch


def test_exact_match():
    register("help", "help_handler")
    assert dispatch("help") == "help_handler"


def test_missing_command():
    assert dispatch("unknown") is None


def test_multiple_commands():
    register("start", "start_handler")
    register("stop", "stop_handler")
    assert dispatch("start") == "start_handler"
    assert dispatch("stop") == "stop_handler"
''',
    "hidden_test": '''from task_095_lib.commands import register, dispatch


def test_uppercase_dispatch():
    register("help", "help_handler")
    assert dispatch("HELP") == "help_handler"


def test_mixed_case_register_and_dispatch():
    register("MyCmd", "my_handler")
    assert dispatch("mycmd") == "my_handler"
    assert dispatch("MYCMD") == "my_handler"
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Exact-case registration and dispatch works, but different casing fails.",
    "generalization_axis": "Public covers exact-case match; hidden covers case-insensitive dispatch.",
}

TASKS["task_096"] = {
    "bug_type": "multi_file_integration",
    "package": "task_096_lib",
    "files": {
        "task_096_lib/__init__.py": ("", ""),
        "task_096_lib/models.py": (
            '''from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
''',
            '''from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    quantity: int = 1
''',
        ),
        "task_096_lib/cart.py": (
            '''from __future__ import annotations

from task_096_lib.models import Item


def cart_total(items: list[Item]) -> float:
    return sum(item.price for item in items)
''',
            '''from __future__ import annotations

from task_096_lib.models import Item


def cart_total(items: list[Item]) -> float:
    return sum(item.price * item.quantity for item in items)
''',
        ),
    },
    "target_functions": ["Item", "cart_total"],
    "issue": """# Cart total ignores item quantity

`cart_total` should multiply each item's price by its quantity, but `Item` has no `quantity` field and `cart_total` only sums prices.
""",
    "public_test": '''from task_096_lib.models import Item
from task_096_lib.cart import cart_total


def test_single_item():
    items = [Item(name="apple", price=1.0)]
    assert cart_total(items) == 1.0


def test_multiple_items():
    items = [Item(name="a", price=10.0), Item(name="b", price=5.0)]
    assert cart_total(items) == 15.0
''',
    "hidden_test": '''from task_096_lib.models import Item
from task_096_lib.cart import cart_total


def test_quantity_is_factored_in():
    items = [Item(name="apple", price=1.0, quantity=3)]
    assert cart_total(items) == 3.0


def test_mixed_quantities():
    items = [
        Item(name="a", price=2.0, quantity=5),
        Item(name="b", price=10.0, quantity=1),
    ]
    assert cart_total(items) == 20.0
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Sum-of-prices works, but quantity is missing from both model and computation.",
    "generalization_axis": "Public covers price-only sums; hidden covers quantity-weighted totals.",
}

TASKS["task_097"] = {
    "bug_type": "stateful_side_effect",
    "package": "task_097_lib",
    "files": {
        "task_097_lib/limiter.py": (
            '''from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) < self.max_calls:
            self._timestamps.append(now)
            return True
        return False

    def reset(self) -> None:
        self._timestamps = []
''',
            '''from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._timestamps: list[float] = []
        self._blocked_count: int = 0

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) < self.max_calls:
            self._timestamps.append(now)
            return True
        self._blocked_count += 1
        return False

    def reset(self) -> None:
        self._timestamps = []
        self._blocked_count = 0
''',
        )
    },
    "target_functions": ["RateLimiter.allow", "RateLimiter.reset"],
    "issue": """# RateLimiter does not track blocked requests

`RateLimiter` should count how many requests have been blocked due to rate limiting. The counter must reset when `reset()` is called.
""",
    "public_test": '''from task_097_lib.limiter import RateLimiter


def test_allows_within_limit():
    rl = RateLimiter(max_calls=3, window_seconds=60)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is True


def test_blocks_over_limit():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    assert rl.allow() is True
    assert rl.allow() is False


def test_reset_clears_window():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.reset()
    assert rl.allow() is True
''',
    "hidden_test": '''from task_097_lib.limiter import RateLimiter


def test_blocked_count_increments():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.allow()
    rl.allow()
    assert rl._blocked_count == 2


def test_reset_clears_blocked_count():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.allow()
    rl.reset()
    assert rl._blocked_count == 0
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Allow/deny and reset work, but blocked-count state is missing.",
    "generalization_axis": "Public covers basic allow/deny/reset; hidden covers blocked-count tracking.",
}

TASKS["task_098"] = {
    "bug_type": "idempotency",
    "package": "task_098_lib",
    "files": {
        "task_098_lib/seed.py": (
            '''from __future__ import annotations

_SEEDED: bool = False


def ensure_seeded(seed: int = 42) -> None:
    global _SEEDED
    if not _SEEDED:
        import random
        random.seed(seed)
        _SEEDED = True
''',
            '''from __future__ import annotations

_SEEDED: int | None = None


def ensure_seeded(seed: int = 42) -> None:
    global _SEEDED
    if _SEEDED is None:
        import random
        random.seed(seed)
        _SEEDED = seed
    elif _SEEDED != seed:
        raise RuntimeError(f"already seeded with {_SEEDED}, refusing {seed}")
''',
        )
    },
    "target_functions": ["ensure_seeded"],
    "issue": """# ensure_seeded silently ignores conflicting seeds

`ensure_seeded` should raise `RuntimeError` if called with a different seed after the first successful call, so that accidental re-seeding with a conflicting value is caught.
""",
    "public_test": '''from task_098_lib.seed import ensure_seeded


def test_first_call_works():
    import random
    ensure_seeded(42)
    a = random.random()
    random.seed(42)
    b = random.random()
    assert a == b
''',
    "hidden_test": '''from task_098_lib.seed import ensure_seeded


def test_conflicting_seed_raises():
    ensure_seeded(42)
    try:
        ensure_seeded(99)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError for conflicting seed")
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "First call works, but second call with a different seed is silently ignored.",
    "generalization_axis": "Public covers initial seeding; hidden covers conflict detection.",
}

TASKS["task_099"] = {
    "bug_type": "validation_logic",
    "package": "task_099_lib",
    "files": {
        "task_099_lib/password_check.py": (
            '''from __future__ import annotations


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
    )
''',
            '''from __future__ import annotations


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and not password.isalnum()
    )
''',
        )
    },
    "target_functions": ["is_strong_password"],
    "issue": """# Password strength checker does not require special characters

`is_strong_password` should require at least one non-alphanumeric character to prevent easily guessable passwords like `"Password1"`.
""",
    "public_test": '''from task_099_lib.password_check import is_strong_password


def test_strong_password():
    assert is_strong_password("Str0ng!Pass") is True


def test_too_short():
    assert is_strong_password("Ab1!") is False


def test_missing_digit():
    assert is_strong_password("Abcdefgh!") is False


def test_missing_uppercase():
    assert is_strong_password("abcdefgh1!") is False
''',
    "hidden_test": '''from task_099_lib.password_check import is_strong_password


def test_no_special_char_is_weak():
    assert is_strong_password("Password1") is False


def test_all_alphanumeric_is_weak():
    assert is_strong_password("Abcd1234") is False


def test_single_special_char_ok():
    assert is_strong_password("Abcd1234!") is True
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "Length/case/digit checks work, but passwords without special characters are accepted.",
    "generalization_axis": "Public covers basic complexity rules; hidden covers special-character requirement.",
}

TASKS["task_100"] = {
    "bug_type": "config_merge",
    "package": "task_100_lib",
    "files": {
        "task_100_lib/layered.py": (
            '''from __future__ import annotations


def layered_merge(*layers: dict) -> dict:
    result: dict = {}
    for layer in layers:
        for key, value in layer.items():
            if isinstance(value, list) and key in result and isinstance(result[key], list):
                result[key] = result[key] + value
            else:
                result[key] = value
    return result
''',
            '''from __future__ import annotations


def layered_merge(*layers: dict) -> dict:
    result: dict = {}
    for layer in layers:
        for key, value in layer.items():
            if (
                isinstance(value, list)
                and key in result
                and isinstance(result[key], list)
            ):
                result[key] = result[key] + value
            elif (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                result[key] = layered_merge(result[key], value)
            else:
                result[key] = value
    return result
''',
        )
    },
    "target_functions": ["layered_merge"],
    "issue": """# Layered config merge overwrites nested dicts

`layered_merge` correctly concatenates list values across layers, but it should also deep-merge nested dict values instead of overwriting them.
""",
    "public_test": '''from task_100_lib.layered import layered_merge


def test_lists_are_concatenated():
    a = {"tags": ["a", "b"]}
    b = {"tags": ["c"]}
    result = layered_merge(a, b)
    assert result["tags"] == ["a", "b", "c"]


def test_scalar_is_overwritten():
    result = layered_merge({"x": 1}, {"x": 2})
    assert result["x"] == 2


def test_new_key_is_added():
    result = layered_merge({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}
''',
    "hidden_test": '''from task_100_lib.layered import layered_merge


def test_nested_dicts_are_deep_merged():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"host": "prod.example.com"}}
    result = layered_merge(base, override)
    assert result["db"]["host"] == "prod.example.com"
    assert result["db"]["port"] == 5432


def test_deep_nested_dicts():
    a = {"a": {"b": {"x": 1}}}
    b = {"a": {"b": {"y": 2}}}
    result = layered_merge(a, b)
    assert result["a"]["b"]["x"] == 1
    assert result["a"]["b"]["y"] == 2
''',
    "expected_buggy": ("pass", "fail"),
    "expected_failure_mode": "List concatenation and scalar overwrites work, but nested dicts are replaced instead of merged.",
    "generalization_axis": "Public covers scalar and list merge; hidden covers nested-dict deep merge.",
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


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
    difficulty = "easy"
    metadata = {
        "task_id": task_id,
        "bug_type": spec["bug_type"],
        "difficulty": difficulty,
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "target_files": target_files,
        "target_functions": spec["target_functions"],
        "expected_failure_mode": spec["expected_failure_mode"],
        "generalization_axis": spec["generalization_axis"],
        "repo_path": str(Path("data/mini_repo_debug/repos") / task_id),
        "source": "manual_p61_expansion",
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
    assert len(TASKS) == 40, f"expected 40 tasks, got {len(TASKS)}"
    for task_id in TASK_IDS:
        write_task(task_id, TASKS[task_id])
        check_patch_applies(task_id)
    hard_pair_count = 0
    for task_id in TASK_IDS:
        verify_task(task_id, TASKS[task_id])
        spec = TASKS[task_id]
        if spec["expected_buggy"] == ("pass", "fail"):
            hard_pair_count += 1
    print(f"\nPASS: P61 task_061-task_100 repair and verification complete")
    print(f"Hard-pair tasks: {hard_pair_count}/40")


if __name__ == "__main__":
    main()
