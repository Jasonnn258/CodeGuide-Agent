import json
from pathlib import Path
from unittest.mock import patch

from codeguide_agent.eval.run_eval import compute_repo_checksum
from codeguide_agent.eval_compare import compare_policies
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.llm_client import MockLLMClient
from codeguide_agent.rollout.llm_config import LLMConfig
from codeguide_agent.rollout.llm_policy import LLMPolicy
from codeguide_agent.rollout.prompts import build_llm_prompt


def test_mock_llm_policy_runs_without_api_key(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=LLMPolicy(config=LLMConfig(backend="mock", mock=True, max_calls_per_task=4)),
        temp_root=tmp_path / "eval",
        max_steps=4,
        run_hidden=False,
    )

    assert result["policy"] == "llm"
    assert result["llm_calls"] > 0
    assert Path(result["trajectory_path"]).exists()
    assert result["original_repo_unchanged"] is True
    assert "total_reward" in result["reward"]


def test_llm_prompt_excludes_forbidden_and_gold_metadata():
    prompt = build_llm_prompt(
        issue_text="The parser fails on nested config.",
        public_test_cmd="python -m pytest tests -q",
        observations=[],
        opened_files=[],
        searched_queries=[],
    )

    forbidden = [
        "metadata.json",
        "gold.patch",
        "tests_hidden",
        "python -m pytest tests_hidden",
        "src/config_loader.py",
        "load_config",
    ]
    for text in forbidden:
        assert text not in prompt


def test_invalid_json_is_retried_once_and_handled_safely(tmp_path: Path):
    client = MockLLMClient(responses=["not json", "also not json"])
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=LLMPolicy(config=LLMConfig(backend="mock", mock=True, max_calls_per_task=2), client=client),
        temp_root=tmp_path / "eval",
        max_steps=2,
        run_hidden=False,
    )

    assert result["invalid_json_count"] >= 1
    assert result["llm_calls"] == 2
    assert result["original_repo_unchanged"] is True


def test_forbidden_file_action_is_rejected(tmp_path: Path):
    client = MockLLMClient(responses=[json.dumps({"action": "read_file", "args": {"file_path": "gold.patch"}})])
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=LLMPolicy(config=LLMConfig(backend="mock", mock=True, max_calls_per_task=1), client=client),
        temp_root=tmp_path / "eval",
        max_steps=1,
        run_hidden=False,
    )

    assert result["opened_files"] == []
    assert result["stop_reason"] == "llm_forbidden_action_rejected"
    assert result["reward"]["forbidden_file_access"] is False


def test_llm_policy_does_not_mutate_canonical_repo(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()
    before = compute_repo_checksum(task)

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=LLMPolicy(config=LLMConfig(backend="mock", mock=True, max_calls_per_task=3)),
        temp_root=tmp_path / "eval",
        max_steps=3,
        run_hidden=False,
    )

    assert compute_repo_checksum(task) == before
    assert result["original_repo_unchanged"] is True


def test_eval_compare_includes_llm_mock(tmp_path: Path):
    with patch.dict("os.environ", {"CODEGUIDE_LLM_MOCK": "1"}, clear=False):
        report = compare_policies(
            root="data/mini_repo_debug",
            policies=["heuristic", "llm"],
            limit=1,
            report_path=tmp_path / "eval_compare.json",
            temp_root=tmp_path / "eval",
            trajectories_dir=tmp_path / "trajectories",
        )

    assert report["summary"]["llm"]["availability"] == "mock"
    assert report["summary"]["llm"]["average_llm_calls"] > 0
    assert report["summary"]["llm"]["original_repo_unchanged_rate"] == 1.0
