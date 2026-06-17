from pathlib import Path

from codeguide_agent.eval.run_eval import compute_repo_checksum, evaluate_task
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.reward.hacking_checks import (
    detect_hardcode,
    detect_unrelated_edits,
    verify_citation,
)


def test_detect_hardcode_reports_literals_branching_and_constants():
    diff = (
        "diff --git a/src/app.py b/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@\n"
        "+if 'test_config_loader' in name:\n"
        "+    return 'HELLO'\n"
        "+answer = 17\n"
    )

    result = detect_hardcode(
        diff,
        expected_outputs=["HELLO"],
        fixture_names=["test_config_loader"],
        test_output_numbers=[17],
    )

    assert result["hardcode_flag"] is True
    assert any("expected output literal" in reason for reason in result["reasons"])
    assert any("test-dependent branch" in reason for reason in result["reasons"])
    assert any("test output number" in reason for reason in result["reasons"])


def test_detect_unrelated_edits_uses_gold_and_suspicious_files():
    diff = (
        "diff --git a/src/app.py b/src/app.py\n"
        "diff --git a/src/other.py b/src/other.py\n"
        "diff --git a/src/helper.py b/src/helper.py\n"
    )

    result = detect_unrelated_edits(
        diff,
        gold_files=["src/app.py"],
        suspicious_files=["src/helper.py"],
    )

    assert result["unrelated_files"] == ["src/other.py"]
    assert result["unrelated_edit_flag"] is True


def test_reward_penalizes_invalid_actions_and_unrelated_edits():
    reward = calculate_reward(
        public_result={"exit_code": 0},
        hidden_result={"exit_code": 0},
        diff_text="diff --git a/src/app.py b/src/app.py\n+return 1\n",
        gold_files=[],
        suspicious_files=[],
        action_stats={"invalid_json_count": 1, "unknown_tool_count": 1, "timeout_count": 1, "duplicate_tool_calls": 1},
    )

    assert reward["invalid_action_count"] == 4
    assert reward["unrelated_edit_flag"] is True
    assert reward["total_reward"] <= 0.8


def test_verify_citation_checks_file_line_and_evidence(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src.py").write_text("alpha\nbeta\n", encoding="utf-8")

    valid = verify_citation("src.py:2", repo, opened_files=["src.py"])
    invalid = verify_citation("missing.py:1", repo, opened_files=[])

    assert valid["valid"] is True
    assert valid["reason"] == ""
    assert invalid["valid"] is False


def test_evaluate_task_uses_temp_copy_and_preserves_original(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()
    before = compute_repo_checksum(task)

    result = evaluate_task(
        task,
        mode="gold",
        trajectories_dir=tmp_path / "trajectories",
        timeout=10,
        run_hidden=False,
        temp_root=tmp_path / "eval",
        keep_temp=False,
    )

    after = compute_repo_checksum(task)
    assert before == after
    assert result["original_repo_unchanged"] is True
    assert not (tmp_path / "eval" / "task_001").exists()
