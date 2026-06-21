#!/usr/bin/env python3
from __future__ import annotations

import difflib
import json
import shutil
from pathlib import Path


ROOT = Path("data/mini_repo_debug/repos")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def make_patch(rel: str, before: str, after: str) -> str:
    def norm_lines(text: str) -> list[str]:
        return [line + "\\n" for line in text.strip("\\n").splitlines()]

    lines = [f"diff --git a/{rel} b/{rel}\\n"]
    lines.extend(
        difflib.unified_diff(
            norm_lines(before),
            norm_lines(after),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
    )
    return "".join(lines)


TASKS = {
    "task_021": {
        "bug_type": "string_normalization",
        "difficulty": "easy",
        "package": "task_021_lib",
        "module": "normalizer.py",
        "target_function": "normalize_label",
        "issue": """# Normalize product labels consistently

The `normalize_label` helper is used before comparing product labels.

It should normalize user-facing labels into a stable canonical form. The current implementation handles only the simplest case and fails on common formatting differences.

Please fix the implementation without changing the public API.
""",
        "before": '''from __future__ import annotations


def normalize_label(label: str) -> str:
    """Return a normalized product label."""
    return label.lower()
''',
        "after": '''from __future__ import annotations

import re
import string


def normalize_label(label: str) -> str:
    """Return a normalized product label."""
    cleaned = label.strip().lower()
    cleaned = cleaned.translate(str.maketrans("", "", string.punctuation))
    cleaned = re.sub(r"\\s+", " ", cleaned)
    return cleaned
''',
        "public_test": '''from task_021_lib.normalizer import normalize_label


def test_lowercase_and_strip():
    assert normalize_label("  Running Shoe  ") == "running shoe"


def test_simple_case_insensitive_match():
    assert normalize_label("HOODIE") == "hoodie"
''',
        "hidden_test": '''from task_021_lib.normalizer import normalize_label


def test_collapses_repeated_spaces():
    assert normalize_label("Running    Shoe") == "running shoe"


def test_removes_punctuation():
    assert normalize_label("Men's Jacket!!!") == "mens jacket"
''',
        "expected_failure_mode": "Patch only lowercases or strips simple whitespace but misses repeated spaces and punctuation.",
        "generalization_axis": "Public covers simple case and strip; hidden covers punctuation and whitespace normalization.",
    },
    "task_022": {
        "bug_type": "path_handling",
        "difficulty": "medium",
        "package": "task_022_lib",
        "module": "paths.py",
        "target_function": "safe_join",
        "issue": """# Safely resolve user-provided report paths

The report loader joins a base directory with a user-provided path.

The helper should keep paths inside the base directory and normalize harmless relative path syntax. It should reject paths that escape the base directory.

Please fix the helper without changing its function signature.
""",
        "before": '''from __future__ import annotations

from pathlib import Path


def safe_join(base_dir: str, user_path: str) -> str:
    return str(Path(base_dir) / user_path)
''',
        "after": '''from __future__ import annotations

from pathlib import Path


def safe_join(base_dir: str, user_path: str) -> str:
    base = Path(base_dir).resolve()
    candidate = (base / user_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("path escapes base directory") from exc
    return str(candidate)
''',
        "public_test": '''from pathlib import Path

from task_022_lib.paths import safe_join


def test_normalizes_simple_relative_path(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    result = safe_join(str(base), "./daily.txt")
    assert Path(result).resolve() == (base / "daily.txt").resolve()


def test_nested_relative_path(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    result = safe_join(str(base), "2026/june.txt")
    assert Path(result).resolve() == (base / "2026" / "june.txt").resolve()
''',
        "hidden_test": '''import pytest

from task_022_lib.paths import safe_join


def test_rejects_parent_directory_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    with pytest.raises(ValueError):
        safe_join(str(base), "../secret.txt")


def test_rejects_absolute_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    with pytest.raises(ValueError):
        safe_join(str(base), str(outside))
''',
        "expected_failure_mode": "Patch joins paths naively and does not prevent parent-directory or absolute path escape.",
        "generalization_axis": "Public covers harmless normalization; hidden covers escaping the base directory.",
    },
    "task_023": {
        "bug_type": "cache_key",
        "difficulty": "medium",
        "package": "task_023_lib",
        "module": "cache.py",
        "target_function": "make_cache_key",
        "issue": """# Build parameter-sensitive cache keys

The cache key helper is used by a small service wrapper.

Different calls with different parameters should not collide. The current helper is too coarse and can reuse stale results across different inputs.

Please make the key stable and parameter-sensitive.
""",
        "before": '''from __future__ import annotations

from typing import Any


def make_cache_key(name: str, params: dict[str, Any]) -> str:
    return name
''',
        "after": '''from __future__ import annotations

import json
from typing import Any


def make_cache_key(name: str, params: dict[str, Any]) -> str:
    encoded = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return f"{name}:{encoded}"
''',
        "public_test": '''from task_023_lib.cache import make_cache_key


def test_different_params_do_not_collide():
    assert make_cache_key("search", {"q": "shoe"}) != make_cache_key("search", {"q": "bag"})


def test_same_params_have_same_key_even_if_order_differs():
    assert make_cache_key("search", {"q": "shoe", "page": 1}) == make_cache_key("search", {"page": 1, "q": "shoe"})
''',
        "hidden_test": '''from task_023_lib.cache import make_cache_key


def test_nested_params_are_stable():
    a = {"filters": {"color": "black", "sizes": ["M", "L"]}, "page": 1}
    b = {"page": 1, "filters": {"sizes": ["M", "L"], "color": "black"}}
    assert make_cache_key("search", a) == make_cache_key("search", b)


def test_name_is_part_of_key():
    params = {"id": 7}
    assert make_cache_key("product", params) != make_cache_key("seller", params)
''',
        "expected_failure_mode": "Patch keys only on function name or unsorted params, causing collisions or unstable keys.",
        "generalization_axis": "Public covers simple param differences; hidden covers nested stable serialization and function-name separation.",
    },
    "task_024": {
        "bug_type": "optional_default_args",
        "difficulty": "medium",
        "package": "task_024_lib",
        "module": "tags.py",
        "target_function": "add_tag",
        "issue": """# Add a tag without leaking mutable state

The `add_tag` helper returns a list of tags with a new tag appended.

It should work both when no existing tags are provided and when the caller passes an existing list. The caller's list should not be mutated.

Please fix the implementation without changing the public API.
""",
        "before": '''from __future__ import annotations


def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    if tags is None:
        tags = []
    tags.append(tag)
    return tags
''',
        "after": '''from __future__ import annotations


def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    result = list(tags) if tags is not None else []
    result.append(tag)
    return result
''',
        "public_test": '''from task_024_lib.tags import add_tag


def test_omitted_tags_do_not_share_state():
    assert add_tag("new") == ["new"]
    assert add_tag("sale") == ["sale"]


def test_appends_to_existing_tags():
    assert add_tag("new", ["shoe"]) == ["shoe", "new"]
''',
        "hidden_test": '''from task_024_lib.tags import add_tag


def test_does_not_mutate_caller_list():
    original = ["shoe"]
    result = add_tag("new", original)
    assert result == ["shoe", "new"]
    assert original == ["shoe"]


def test_empty_explicit_list_is_not_reused():
    tags = []
    assert add_tag("a", tags) == ["a"]
    assert tags == []
''',
        "expected_failure_mode": "Patch fixes None default but still mutates caller-provided list.",
        "generalization_axis": "Public covers omitted and basic append; hidden covers explicit mutable input aliasing.",
    },
    "task_025": {
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "package": "task_025_lib",
        "module": "stats.py",
        "target_function": "moving_average",
        "issue": """# Include all valid moving-average windows

The analytics helper computes a simple moving average over a list of numbers.

It should include every valid window, including the final window. It should also handle boundary inputs explicitly.

Please fix the implementation without changing its public API.
""",
        "before": '''from __future__ import annotations


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        return []
    return [
        sum(values[i : i + window]) / window
        for i in range(0, len(values) - window)
    ]
''',
        "after": '''from __future__ import annotations


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        return []
    return [
        sum(values[i : i + window]) / window
        for i in range(0, len(values) - window + 1)
    ]
''',
        "public_test": '''from task_025_lib.stats import moving_average


def test_includes_final_window():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_equal_length():
    assert moving_average([2, 4, 6], 3) == [4.0]
''',
        "hidden_test": '''import pytest

from task_025_lib.stats import moving_average


def test_empty_when_not_enough_values():
    assert moving_average([1], 2) == []


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)
''',
        "expected_failure_mode": "Patch handles common ranges but misses last valid window or boundary behavior.",
        "generalization_axis": "Public covers final-window off-by-one; hidden covers too-short input and invalid window.",
    },
}


def build_task(task_id: str, spec: dict[str, str]) -> None:
    task_dir = ROOT / task_id
    if task_dir.exists():
        raise SystemExit(f"{task_dir} already exists; refusing to overwrite")

    package = spec["package"]
    module = spec["module"]
    rel = f"{package}/{module}"

    write(task_dir / "issue.md", spec["issue"])
    write(task_dir / package / "__init__.py", "")
    write(task_dir / package / module, spec["before"])
    write(task_dir / "tests" / f"test_{task_id}_public.py", spec["public_test"])
    write(task_dir / "tests_hidden" / f"test_{task_id}_hidden.py", spec["hidden_test"])

    spec.setdefault("scenario", spec["generalization_axis"])
    spec.setdefault("forbidden_behaviors", [
        spec["expected_failure_mode"],
        "hard-code public examples",
        "leak hidden tests or gold patch",
    ])

    metadata = {
        "task_id": task_id,
        "repo_path": str(task_dir),
        "source": "manual_p32_expansion",
        "split": "train",
        "scenario": spec["scenario"],
        "bug_type": spec["bug_type"],
        "difficulty": spec["difficulty"],
        "issue_path": "issue.md",
        "public_test_cmd": "python -m pytest tests -q",
        "hidden_test_cmd": "python -m pytest tests_hidden -q",
        "gold_patch": "gold.patch",
        "gold_files": [rel],
        "gold_functions": [spec["target_function"]],
        "forbidden_behaviors": spec["forbidden_behaviors"],
        "target_files": [rel],
        "target_functions": [spec["target_function"]],
        "expected_failure_mode": spec["expected_failure_mode"],
        "generalization_axis": spec["generalization_axis"],
    }
    write(task_dir / "metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

    patch = make_patch(rel, spec["before"], spec["after"])
    write(task_dir / "gold.patch", patch)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for task_id, spec in TASKS.items():
        build_task(task_id, spec)
        print("created", ROOT / task_id)


if __name__ == "__main__":
    main()
