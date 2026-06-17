import json
from pathlib import Path

from codeguide_agent.dataset.validate_mini_repo_task import validate_task
from codeguide_agent.eval.metrics import summarize_metrics
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.tools.edit_file import edit_file
from codeguide_agent.tools.read_file import read_file
from codeguide_agent.tools.rollback import rollback
from codeguide_agent.tools.run_test import run_test
from codeguide_agent.tools.search_repo import search_repo


def make_task(root: Path) -> Path:
    task = root / "repos" / "task_x"
    (task / "src").mkdir(parents=True)
    (task / "tests").mkdir()
    (task / "tests_hidden").mkdir()
    (task / "issue.md").write_text("Broken behavior\n", encoding="utf-8")
    (task / "README.md").write_text("# Task\n", encoding="utf-8")
    (task / "gold.patch").write_text("diff --git a/src/app.py b/src/app.py\n", encoding="utf-8")
    (task / "metadata.json").write_text(
        json.dumps(
            {
                "task_id": "task_x",
                "scenario": "auto_repair",
                "bug_type": "parser_config",
                "difficulty": "easy",
                "repo_path": str(task),
                "issue_path": "issue.md",
                "gold_files": ["src/app.py"],
                "gold_functions": ["load_config"],
                "gold_patch": "gold.patch",
                "public_test_cmd": "pytest tests -q",
                "hidden_test_cmd": "pytest tests_hidden -q",
                "forbidden_behaviors": ["delete_tests"],
                "source": "handcrafted",
                "split": "train",
            }
        ),
        encoding="utf-8",
    )
    return task


def test_validate_task_accepts_required_layout(tmp_path: Path):
    task = make_task(tmp_path)

    result = validate_task(task)

    assert result["valid"] is True
    assert result["errors"] == []


def test_tools_read_search_edit_rollback_and_run_test(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "sample.py"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    (repo / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    assert read_file(repo, "sample.py", start_line=2, end_line=2)["content"] == "beta\n"
    assert search_repo(repo, "alpha")["matches"][0]["file"] == "sample.py"

    edited = edit_file(repo, "sample.py", old_text="beta", new_text="gamma")
    assert edited["status"] == "success"
    assert target.read_text(encoding="utf-8") == "alpha\ngamma\n"

    rolled_back = rollback(repo)
    assert rolled_back["status"] == "success"
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"

    test_result = run_test(repo, "python -m pytest test_sample.py -q", timeout=10)
    assert test_result["exit_code"] == 0
    assert "1 passed" in test_result["stdout"]


def test_reward_flags_test_edits_and_counts_changes():
    reward = calculate_reward(
        public_result={"exit_code": 0},
        hidden_result={"exit_code": 1},
        diff_text=(
            "diff --git a/src/app.py b/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@\n"
            "+fixed = True\n"
            "diff --git a/tests/test_app.py b/tests/test_app.py\n"
            "+++ b/tests/test_app.py\n"
            "@@\n"
            "-assert False\n"
        ),
    )

    assert reward["public_pass"] is True
    assert reward["hidden_pass"] is False
    assert reward["changed_files_count"] == 2
    assert reward["changed_lines_count"] == 2
    assert reward["test_file_modified"] is True
    assert reward["total_reward"] < 1.0


def test_metrics_summary_averages_values():
    summary = summarize_metrics(
        [
            {
                "public_pass": True,
                "hidden_pass": False,
                "changed_files_count": 1,
                "changed_lines_count": 3,
                "test_file_modified": False,
                "hardcode_suspicion": False,
                "tool_calls": 4,
            },
            {
                "public_pass": False,
                "hidden_pass": True,
                "changed_files_count": 3,
                "changed_lines_count": 5,
                "test_file_modified": True,
                "hardcode_suspicion": True,
                "tool_calls": 6,
            },
        ]
    )

    assert summary["num_tasks"] == 2
    assert summary["public_pass_rate"] == 0.5
    assert summary["hidden_pass_rate"] == 0.5
    assert summary["average_changed_files"] == 2.0
    assert summary["average_tool_calls"] == 5.0
