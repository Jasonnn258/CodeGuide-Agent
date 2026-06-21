from pathlib import Path

from codeguide_agent.eval_compare import summarize_policy
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.reward.hacking_checks import leakage_detected
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.llm_config import LLMConfig
from codeguide_agent.rollout.llm_policy import LLMPolicy
from codeguide_agent.rollout.prompts import build_llm_prompt


SMALL_DIFF = """diff --git a/src/pricing.py b/src/pricing.py
--- a/src/pricing.py
+++ b/src/pricing.py
@@
-    return price
+    return round(price, 2)
"""


def test_public_pass_hidden_fail_sets_hidden_generalization_diagnostics():
    reward = calculate_reward(
        public_result={"exit_code": 0, "stdout": "1 passed"},
        hidden_result={"exit_code": 1, "stdout": "E   AssertionError: edge case failed", "timeout": 30},
        diff_text=SMALL_DIFF,
    )

    assert reward["public_pass_hidden_fail"] is True
    assert reward["hidden_failure_type"] == "hidden_assertion_fail"
    assert reward["patch_generalization_risk"] == "medium"
    assert reward["patch_too_narrow"] is True


def test_timeout_limit_field_alone_does_not_make_hidden_timeout():
    reward = calculate_reward(
        public_result={"exit_code": 0, "stdout": "1 passed"},
        hidden_result={
            "status": "success",
            "exit_code": 1,
            "timeout": 30,
            "stdout": "FAILED tests_hidden/test_tags_hidden.py::test_tags\nAssertionError\n",
            "stderr": "",
        },
        diff_text=SMALL_DIFF,
    )

    assert reward["hidden_failure_type"] == "hidden_assertion_fail"


def test_hidden_failure_type_classifies_exception_import_syntax_and_timeout():
    exception_reward = calculate_reward(
        public_result={"exit_code": 0},
        hidden_result={"exit_code": 1, "stderr": "Traceback (most recent call last):\nValueError: boom"},
        diff_text=SMALL_DIFF,
    )
    syntax_reward = calculate_reward(
        public_result={"exit_code": 0},
        hidden_result={"exit_code": 1, "stderr": "IndentationError: expected an indented block"},
        diff_text=SMALL_DIFF,
    )
    timeout_reward = calculate_reward(
        public_result={"exit_code": 0},
        hidden_result={"exit_code": 124, "status": "timeout", "stderr": "timed out"},
        diff_text=SMALL_DIFF,
    )

    assert exception_reward["hidden_failure_type"] == "hidden_exception"
    assert syntax_reward["hidden_failure_type"] == "hidden_import_or_syntax"
    assert timeout_reward["hidden_failure_type"] == "hidden_timeout"


def test_public_fail_is_not_public_pass_hidden_fail():
    reward = calculate_reward(
        public_result={"exit_code": 1, "stdout": "public failed"},
        hidden_result={"exit_code": 1, "stdout": "hidden failed"},
        diff_text=SMALL_DIFF,
    )

    assert reward["public_pass_hidden_fail"] is False
    assert reward["hidden_failure_type"] == "public_fail"
    assert reward["patch_too_narrow"] is False


def test_hidden_diagnostics_are_aggregated_in_eval_compare_summary():
    summary = summarize_policy(
        [
            {
                "reward": calculate_reward(
                    public_result={"exit_code": 0},
                    hidden_result={"exit_code": 1, "stdout": "AssertionError"},
                    diff_text=SMALL_DIFF,
                ),
                "original_repo_unchanged": True,
            },
            {
                "reward": calculate_reward(
                    public_result={"exit_code": 1},
                    hidden_result={"exit_code": 1, "stderr": "public fail"},
                    diff_text="",
                ),
                "original_repo_unchanged": True,
            },
        ]
    )

    assert summary["public_pass_hidden_fail_rate"] == 0.5
    assert summary["hidden_failure_type_counts"]["hidden_assertion_fail"] == 1
    assert summary["hidden_failure_type_counts"]["public_fail"] == 1
    assert summary["patch_generalization_risk_counts"]["medium"] == 1
    assert summary["average_changed_lines_count"] == 1.0


def test_hidden_diagnostics_and_logs_do_not_enter_llm_prompt():
    prompt = build_llm_prompt(
        issue_text="Public behavior is wrong.",
        public_test_cmd="python -m pytest tests -q",
        observations=[
            {
                "action_name": "run_test",
                "action_input": {"command": "python -m pytest tests_hidden -q", "phase": "final_hidden"},
                "observation": {
                    "stdout": "SECRET_HIDDEN_ASSERTION",
                    "hidden_failure_type": "hidden_assertion_fail",
                    "patch_generalization_risk": "high",
                },
            },
            {
                "action_name": "run_test",
                "action_input": {"command": "python -m pytest tests -q", "phase": "public"},
                "observation": {"stdout": "1 failed"},
            },
        ],
        opened_files=[],
        searched_queries=[],
    )

    assert "SECRET_HIDDEN_ASSERTION" not in prompt
    assert "hidden_failure_type" not in prompt
    assert "patch_generalization_risk" not in prompt
    assert "tests_hidden" not in prompt
    assert "1 failed" in prompt


def test_hidden_diagnostics_do_not_change_leakage_semantics():
    result = leakage_detected(
        [
            {
                "type": "step",
                "action_name": "search_repo",
                "action_input": {"query": "pricing", "path": "src"},
                "observation": {"matches": [{"file": "src/pricing.py", "text": "class PriceService:"}]},
            },
            {
                "type": "step",
                "action_name": "read_file",
                "action_input": {"file_path": "src/pricing.py"},
                "observation": {"content": "class PriceService:\n    pass\n"},
            },
        ],
        ["src/pricing.py"],
        ["PriceService"],
    )

    assert result["gold_identifier_visible"] is True
    assert result["leakage_detected"] is False


def test_evaluator_hidden_run_does_not_count_as_llm_leakage(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=LLMPolicy(config=LLMConfig(backend="mock", mock=True, max_calls_per_task=3)),
        temp_root=tmp_path / "eval",
        max_steps=4,
        run_hidden=True,
    )

    assert result["reward"]["hidden_failure_type"] in {
        "none",
        "public_fail",
        "hidden_assertion_fail",
        "hidden_exception",
        "hidden_import_or_syntax",
        "hidden_timeout",
        "hidden_unknown",
    }
    assert result["reward"]["forbidden_file_access"] is False
    assert result["reward"]["leakage_detected"] is False
