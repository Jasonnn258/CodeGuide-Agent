import json
from pathlib import Path
from unittest.mock import patch

from codeguide_agent.baselines import aider_runner
from codeguide_agent.eval.run_eval import compute_repo_checksum
from codeguide_agent.eval_compare import compare_policies


def test_aider_unavailable_writes_skipped_report(tmp_path: Path):
    output = tmp_path / "aider_report.json"

    with patch("codeguide_agent.baselines.aider_runner.shutil.which", return_value=None):
        report = aider_runner.run_aider_baseline(
            root="data/mini_repo_debug",
            limit=1,
            output=output,
            temp_root=tmp_path / "eval",
        )

    assert output.exists()
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["summary"]["available"] is False
    assert saved["summary"]["skip_reason"] == "aider_cli_not_found"
    assert saved["results"][0]["status"] == "skipped"
    assert report["results"][0]["original_repo_unchanged"] is True


def test_aider_prompt_excludes_evaluator_only_paths():
    prompt = aider_runner.build_aider_prompt(
        issue_text="The config parser drops nested values.",
        public_test_cmd="python -m pytest tests -q",
    )

    assert "metadata.json" not in prompt
    assert "gold.patch" not in prompt
    assert "tests_hidden" not in prompt
    assert "python -m pytest tests -q" in prompt
    assert "fix the bug minimally" in prompt.lower()


def test_mocked_aider_result_uses_canonical_reward_fields(tmp_path: Path):
    output = tmp_path / "aider_report.json"
    task = Path("data/mini_repo_debug/repos/task_001").resolve()

    def fake_run(repo_path, prompt, timeout, aider_bin):
        source = Path(repo_path) / "src" / "config_loader.py"
        text = source.read_text(encoding="utf-8")
        source.write_text(text.replace("return {}", "return data"), encoding="utf-8")
        return {
            "exit_code": 0,
            "stdout": "mock aider",
            "stderr": "",
            "command": [aider_bin, "--message", "<redacted>"],
            "timed_out": False,
        }

    with patch("codeguide_agent.baselines.aider_runner.shutil.which", return_value="/usr/local/bin/aider"):
        report = aider_runner.run_aider_baseline(
            root="data/mini_repo_debug",
            limit=1,
            output=output,
            temp_root=tmp_path / "eval",
            env={"OPENAI_API_KEY": "test-key"},
            run_command=fake_run,
        )

    result = report["results"][0]
    assert result["task_id"] == "task_001"
    assert result["status"] in {"success", "fail"}
    assert "total_reward" in result
    assert "reward" in result
    assert result["reward"]["total_reward"] == result["total_reward"]
    assert "gold_file_patched" in result
    assert "gold_function_patched" in result
    assert "leakage_detected" in result
    assert result["original_repo_unchanged"] is True
    assert compute_repo_checksum(task) == result["original_checksum_after"]


def test_eval_compare_includes_skipped_aider(tmp_path: Path):
    with patch("codeguide_agent.baselines.aider_runner.shutil.which", return_value=None):
        report = compare_policies(
            root="data/mini_repo_debug",
            policies=["heuristic", "aider"],
            limit=1,
            report_path=tmp_path / "eval_compare.json",
            temp_root=tmp_path / "eval",
            trajectories_dir=tmp_path / "trajectories",
        )

    assert report["summary"]["aider"]["availability"] == "skipped"
    assert report["summary"]["aider"]["skip_reason"] == "aider_cli_not_found"
    assert report["results"]["aider"][0]["status"] == "skipped"


def test_aider_runner_does_not_mutate_canonical_repo_when_skipped(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()
    before = compute_repo_checksum(task)

    with patch("codeguide_agent.baselines.aider_runner.shutil.which", return_value=None):
        aider_runner.run_aider_baseline(
            root="data/mini_repo_debug",
            limit=1,
            output=tmp_path / "aider_report.json",
            temp_root=tmp_path / "eval",
        )

    assert compute_repo_checksum(task) == before
