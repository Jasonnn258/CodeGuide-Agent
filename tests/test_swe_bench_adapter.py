from __future__ import annotations

import json

from codeguide_agent.eval.swe_bench_adapter import (
    SWEBenchResult,
    SWEBenchTask,
    convert_mini_repo_task,
    evaluate_swe_task,
    load_swe_bench_tasks,
)


# ---------------------------------------------------------------------------
# schema tests
# ---------------------------------------------------------------------------

def test_swe_task_from_dict():
    d = {
        "instance_id": "repo__org.test_001",
        "repo_path": "/tmp/test_repo",
        "problem_statement": "Fix the parsing bug",
        "FAIL_TO_PASS": ["test_parse::test_valid"],
        "PASS_TO_PASS": ["test_parse::test_regression"],
        "test_patch": "diff --git a/tests/test_parse.py b/tests/test_parse.py\n...",
        "gold_patch": "diff --git a/src/parse.py b/src/parse.py\n...",
        "test_command": "python -m pytest tests -q",
    }
    task = SWEBenchTask.from_dict(d)
    assert task.instance_id == "repo__org.test_001"
    assert task.problem_statement == "Fix the parsing bug"
    assert task.fail_to_pass == ["test_parse::test_valid"]
    assert task.pass_to_pass == ["test_parse::test_regression"]


def test_swe_task_from_dict_aliases():
    """Test that alternate field names are handled."""
    d = {
        "task_id": "task_042",
        "repo": "data/repos/task_042",
        "issue": "Fix the sort order",
        "patch": "diff --git ...",
    }
    task = SWEBenchTask.from_dict(d)
    assert task.instance_id == "task_042"
    assert task.repo_path == "data/repos/task_042"
    assert task.problem_statement == "Fix the sort order"
    assert task.gold_patch == "diff --git ..."


def test_swe_task_to_dict_roundtrip():
    task = SWEBenchTask(
        instance_id="test_001",
        repo_path="/tmp/repo",
        problem_statement="Fix bug",
        fail_to_pass=["test_a", "test_b"],
        pass_to_pass=["test_c"],
    )
    d = task.to_dict()
    t2 = SWEBenchTask.from_dict(d)
    assert t2.instance_id == task.instance_id
    assert t2.problem_statement == task.problem_statement
    assert t2.fail_to_pass == task.fail_to_pass


# ---------------------------------------------------------------------------
# result schema
# ---------------------------------------------------------------------------

def test_swe_result_defaults():
    r = SWEBenchResult(instance_id="test_001")
    assert r.resolved is False
    assert r.repo_setup_ok is False
    assert r.patch_applied_ok is False


def test_swe_result_to_dict():
    r = SWEBenchResult(
        instance_id="test_001",
        resolved=True,
        fail_to_pass_passed=2,
        fail_to_pass_total=2,
        pass_to_pass_passed=5,
        pass_to_pass_total=5,
        repo_setup_ok=True,
        patch_applied_ok=True,
        test_output="2 passed",
    )
    d = r.to_dict()
    assert d["resolved"] is True
    assert d["fail_to_pass"]["passed"] == 2
    assert d["patch_applied_ok"] is True


# ---------------------------------------------------------------------------
# task loading
# ---------------------------------------------------------------------------

def test_load_swe_bench_tasks_json_array(tmp_path):
    tasks_json = [
        {"instance_id": "a", "repo_path": "/a", "problem_statement": "fix a"},
        {"instance_id": "b", "repo_path": "/b", "problem_statement": "fix b"},
    ]
    p = tmp_path / "tasks.json"
    p.write_text(json.dumps(tasks_json))
    tasks = load_swe_bench_tasks(p)
    assert len(tasks) == 2
    assert tasks[0].instance_id == "a"
    assert tasks[1].instance_id == "b"


def test_load_swe_bench_tasks_jsonl(tmp_path):
    p = tmp_path / "tasks.jsonl"
    p.write_text(
        '{"instance_id":"a","repo_path":"/a","problem_statement":"fix a"}\n'
        '{"instance_id":"b","repo_path":"/b","problem_statement":"fix b"}\n'
    )
    tasks = load_swe_bench_tasks(p)
    assert len(tasks) == 2


def test_load_swe_bench_tasks_missing_file():
    tasks = load_swe_bench_tasks("/nonexistent/file.json")
    assert tasks == []


# ---------------------------------------------------------------------------
# mini_repo conversion
# ---------------------------------------------------------------------------

def test_convert_mini_repo_task(tmp_path):
    task_dir = tmp_path / "task_001"
    (task_dir / "src").mkdir(parents=True)
    (task_dir / "tests").mkdir()
    (task_dir / "issue.md").write_text("# Fix the parser\n\nThe parser crashes on empty input.")
    (task_dir / "gold.patch").write_text("diff --git a/src/parser.py b/src/parser.py\n-old\n+new\n")
    (task_dir / "tests" / "test_parser.py").write_text(
        "def test_valid_input(): pass\n"
        "def test_empty_input(): pass\n"
        "def test_edge_case(): pass\n"
    )

    task = convert_mini_repo_task(task_dir)
    assert task.instance_id == "task_001"
    assert "Fix the parser" in task.problem_statement
    assert task.gold_patch.startswith("diff --git")
    assert len(task.pass_to_pass) >= 1  # test functions found


# ---------------------------------------------------------------------------
# evaluate_swe_task
# ---------------------------------------------------------------------------

def test_evaluate_gold_patch_resolves(tmp_path):
    """Gold patch applied to its own repo should resolve."""
    task_dir = tmp_path / "task_test"
    src_dir = task_dir / "src"
    tests_dir = task_dir / "tests"
    src_dir.mkdir(parents=True)
    tests_dir.mkdir()

    # Create a buggy module
    (src_dir / "math_utils.py").write_text(
        "def add(a, b):\n    return a - b  # bug: should be a + b\n"
    )
    # Write a standalone test runner script (no pytest dependency)
    (task_dir / "run_tests.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))\n"
        "from math_utils import add\n\n"
        "failures = 0\n"
        "try:\n    assert add(2, 3) == 5, f'Expected 5, got {add(2, 3)}'\n"
        "except AssertionError as e:\n    print(f'FAIL: {e}')\n    failures += 1\n"
        "try:\n    assert add(-1, 5) == 4, f'Expected 4, got {add(-1, 5)}'\n"
        "except AssertionError as e:\n    print(f'FAIL: {e}')\n    failures += 1\n"
        "if failures:\n    print(f'{failures} test(s) failed')\n    sys.exit(1)\n"
        "print('All tests passed')\n"
    )

    gold_patch = (
        "diff --git a/src/math_utils.py b/src/math_utils.py\n"
        "--- a/src/math_utils.py\n"
        "+++ b/src/math_utils.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        "-    return a - b  # bug: should be a + b\n"
        "+    return a + b\n"
    )

    task = SWEBenchTask(
        instance_id="task_test",
        repo_path=str(task_dir),
        problem_statement="Fix the add function",
        fail_to_pass=[],
        pass_to_pass=[],
        test_command="python run_tests.py",
    )

    # Without patch: should fail (bug still present)
    result_empty = evaluate_swe_task(task, "")
    assert not result_empty.resolved
    assert result_empty.error != ""

    # With gold patch: should resolve
    result_fixed = evaluate_swe_task(task, gold_patch)
    assert result_fixed.patch_applied_ok is True
    assert result_fixed.resolved is True


def test_evaluate_bad_patch_does_not_resolve(tmp_path):
    task_dir = tmp_path / "task_bad"
    (task_dir / "src").mkdir(parents=True)
    (task_dir / "src" / "mod.py").write_text("def foo():\n    return 1\n")
    (task_dir / "run_tests.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))\n"
        "from mod import foo\n\n"
        "assert foo() == 2, f'Expected 2, got {foo()}'\n"
        "print('All tests passed')\n"
    )

    # Wrong patch that doesn't fix the bug
    bad_patch = (
        "diff --git a/src/mod.py b/src/mod.py\n"
        "--- a/src/mod.py\n"
        "+++ b/src/mod.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def foo():\n"
        "+    print('hello')\n"
        "     return 1\n"
    )

    task = SWEBenchTask(
        instance_id="task_bad",
        repo_path=str(task_dir),
        problem_statement="Fix foo to return 2",
        test_command="python run_tests.py",
    )

    result = evaluate_swe_task(task, bad_patch)
    assert result.patch_applied_ok is True
    assert result.resolved is False  # patch doesn't fix the test


def test_evaluate_missing_repo():
    task = SWEBenchTask(
        instance_id="missing",
        repo_path="/nonexistent/repo",
        problem_statement="Fix bug",
    )
    result = evaluate_swe_task(task, "diff --git ...")
    assert result.resolved is False
    assert "not found" in result.error
