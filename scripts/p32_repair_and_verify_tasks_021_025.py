#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT / "data" / "mini_repo_debug" / "repos"
TASK_IDS = [f"task_{i:03d}" for i in range(21, 26)]


PUBLIC_OVERRIDES = {
    "task_022": '''from pathlib import Path

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
}


HIDDEN_OVERRIDES = {
    "task_022": '''from task_022_lib.paths import safe_join


def test_rejects_parent_directory_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    try:
        safe_join(str(base), "../secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rejects_absolute_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    try:
        safe_join(str(base), str(outside))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
''',
    "task_025": '''from task_025_lib.stats import moving_average


def test_empty_when_not_enough_values():
    assert moving_average([1], 2) == []


def test_invalid_window_raises():
    try:
        moving_average([1, 2, 3], 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
''',
}


EXPECTED_BUGGY_SHAPE = {
    # public, hidden
    "task_021": ("fail", "fail"),
    "task_022": ("pass", "fail"),
    "task_023": ("fail", "pass"),
    "task_024": ("pass", "fail"),
    "task_025": ("fail", "pass"),
}


METADATA_FIXES = {
    "task_021": {
        "scenario": "string normalization public-hidden generalization",
        "forbidden_behaviors": [
            "hard-code public examples",
            "ignore punctuation",
            "ignore repeated whitespace",
        ],
    },
    "task_022": {
        "scenario": "safe path handling and directory escape prevention",
        "forbidden_behaviors": [
            "join paths without resolving",
            "allow parent-directory escape",
            "allow absolute path escape",
        ],
    },
    "task_023": {
        "scenario": "parameter-sensitive cache key generation",
        "forbidden_behaviors": [
            "cache only by function name",
            "use unstable dict ordering",
            "ignore nested parameters",
        ],
    },
    "task_024": {
        "scenario": "optional mutable input aliasing",
        "forbidden_behaviors": [
            "mutate caller-provided list",
            "reuse mutable state",
            "only handle omitted argument",
        ],
    },
    "task_025": {
        "scenario": "moving average boundary condition",
        "forbidden_behaviors": [
            "drop final valid window",
            "ignore invalid window",
            "special-case only public examples",
        ],
    },
}


def run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def must_run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = run(cmd, cwd, env=env)
    if proc.returncode != 0:
        print(proc.stdout)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return proc


def load_generator_tasks() -> dict:
    path = ROOT / "scripts" / "create_p32_tasks_021_025.py"
    spec = importlib.util.spec_from_file_location("p32_tasks", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TASKS


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def fix_tests(task_id: str) -> None:
    task_dir = REPO_ROOT / task_id
    if task_id in PUBLIC_OVERRIDES:
        write(task_dir / "tests" / f"test_{task_id}_public.py", PUBLIC_OVERRIDES[task_id])
    if task_id in HIDDEN_OVERRIDES:
        write(task_dir / "tests_hidden" / f"test_{task_id}_hidden.py", HIDDEN_OVERRIDES[task_id])


def fix_metadata(task_id: str, task: dict) -> None:
    task_dir = REPO_ROOT / task_id
    rel = task["package"] + "/" + task["module"]
    metadata_path = task_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    metadata.update(
        {
            "task_id": task_id,
            "repo_path": str(Path("data/mini_repo_debug/repos") / task_id),
            "source": "manual_p32_expansion",
            "split": "train",
            "scenario": METADATA_FIXES[task_id]["scenario"],
            "gold_patch": "gold.patch",
            "gold_files": [rel],
            "gold_functions": [task["target_function"]],
            "forbidden_behaviors": METADATA_FIXES[task_id]["forbidden_behaviors"],
            "target_files": [rel],
            "target_functions": [task["target_function"]],
        }
    )

    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regenerate_gold_patch(task_id: str, task: dict) -> None:
    task_dir = REPO_ROOT / task_id
    rel = Path(task["package"]) / task["module"]

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / task_id
        shutil.copytree(task_dir, tmp)

        must_run(["git", "init", "-q"], tmp)
        must_run(["git", "config", "user.email", "codeguide@example.com"], tmp)
        must_run(["git", "config", "user.name", "CodeGuide"], tmp)
        must_run(["git", "add", "."], tmp)
        must_run(["git", "commit", "-q", "-m", "buggy"], tmp)

        (tmp / rel).write_text(task["after"].rstrip() + "\n", encoding="utf-8")

        proc = must_run(["git", "diff", "--binary", "--", str(rel)], tmp)
        patch = proc.stdout
        if not patch.startswith("diff --git"):
            raise SystemExit(f"{task_id}: generated patch is invalid")

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


def simple_pytest(targets: list[Path], cwd: Path, extra_pythonpath: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(extra_pythonpath) + os.pathsep + str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "codeguide_agent.testing.simple_pytest"]
    cmd.extend(str(t) for t in targets)
    cmd.append("-q")
    return run(cmd, ROOT, env=env)


def verify_task(task_id: str) -> None:
    task_dir = REPO_ROOT / task_id

    public_proc = simple_pytest([task_dir / "tests"], ROOT, task_dir)
    hidden_proc = simple_pytest([task_dir / "tests_hidden"], ROOT, task_dir)

    expected_public, expected_hidden = EXPECTED_BUGGY_SHAPE[task_id]
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
        gold_proc = simple_pytest([tmp / "tests", tmp / "tests_hidden"], ROOT, tmp)
        if gold_proc.returncode != 0:
            print(f"\n{task_id}: gold patch failed tests")
            print(gold_proc.stdout)
            raise SystemExit(1)

    print(
        f"PASS {task_id}: buggy public={actual_public}, buggy hidden={actual_hidden}, gold=pass"
    )


def main() -> None:
    tasks = load_generator_tasks()

    missing = [task_id for task_id in TASK_IDS if task_id not in tasks]
    if missing:
        raise SystemExit(f"generator missing tasks: {missing}")

    for task_id in TASK_IDS:
        if not (REPO_ROOT / task_id).exists():
            raise SystemExit(f"missing task dir: {REPO_ROOT / task_id}")

    for task_id in TASK_IDS:
        task = tasks[task_id]
        fix_tests(task_id)
        fix_metadata(task_id, task)
        regenerate_gold_patch(task_id, task)
        check_patch_applies(task_id)

    for task_id in TASK_IDS:
        verify_task(task_id)

    print("PASS: P32 task_021-task_025 repair and verification complete")


if __name__ == "__main__":
    main()
