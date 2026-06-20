import json
from pathlib import Path

from codeguide_agent.evaluators.localization_eval import localization_process_metrics, patch_localization_metrics
from codeguide_agent.reward.hacking_checks import leakage_detected
from codeguide_agent.rollout.actions import Action
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import BasePolicy, GoldPatchPolicy


class BlindBadPatchPolicy(BasePolicy):
    name = "blind_bad_patch"

    def next_action(self, state):
        if not state.edited_files:
            return Action(
                "Break a previously passing behavior without searching first.",
                "edit_file",
                {
                    "file_path": "src/text_cli.py",
                    "old_text": "return text.lower()",
                    "new_text": "return text",
                },
            )
        return Action("Stop after bad patch.", "stop", {"reason": "bad_patch_done"})


def test_patch_hit_and_process_hit_can_disagree(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("def fix_me():\n    return 1\n", encoding="utf-8")
    diff = "diff --git a/src/app.py b/src/app.py\n+++ b/src/app.py\n@@\n-return 1\n+return 2\n"

    patch_metrics = patch_localization_metrics(diff, repo, ["src/app.py"], ["fix_me"])
    process_metrics = localization_process_metrics([], repo, ["src/app.py"], ["fix_me"])

    assert patch_metrics["gold_file_patched"] is True
    assert process_metrics["gold_file_hit_at_3"] is False


def test_gold_policy_patch_without_search_has_no_process_localization_hit(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=GoldPatchPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=4,
        run_hidden=False,
    )

    reward = result["reward"]
    assert reward["gold_file_patched"] is True
    assert reward["gold_file_hit_at_3"] is False


def test_leakage_detected_flags_gold_values_and_forbidden_paths():
    rows = [
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "gold.patch"},
            "observation": {"content": "see src/config_loader.py and load_config"},
        }
    ]

    result = leakage_detected(rows, ["src/config_loader.py"], ["load_config"])

    assert result["leakage_detected"] is True
    assert result["forbidden_file_access"] is True
    assert result["oracle_metadata_leakage"] is True
    assert result["leaked_gold_files"] == ["src/config_loader.py"]
    assert result["leaked_gold_functions"] == ["load_config"]


def test_gold_identifier_visible_from_search_is_not_leakage():
    rows = [
        {
            "type": "step",
            "action_name": "search_repo",
            "action_input": {"query": "yaml", "path": "src"},
            "observation": {"matches": [{"file": "src/config_loader.py", "line": 7, "text": "def load_config(path):"}]},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/config_loader.py"},
            "observation": {"content": "def load_config(path):\n    return {}\n"},
        },
    ]

    result = leakage_detected(rows, ["src/config_loader.py"], ["load_config"])

    assert result["gold_identifier_visible"] is True
    assert result["leakage_detected"] is False
    assert result["forbidden_file_access"] is False
    assert result["oracle_metadata_leakage"] is False


def test_public_traceback_can_legally_surface_gold_file_and_function():
    rows = [
        {
            "type": "step",
            "action_name": "run_test",
            "action_input": {"command": "python -m pytest tests -q", "phase": "pre_public"},
            "observation": {
                "stdout": (
                    "File \"/tmp/task/src/summarizer.py\", line 11, in total_amount\n"
                    "ValueError: invalid literal for int()"
                )
            },
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/summarizer.py"},
            "observation": {"content": "def total_amount(csv_text):\n    return 0\n"},
        },
    ]

    result = leakage_detected(rows, ["src/summarizer.py"], ["total_amount"])

    assert result["gold_identifier_visible"] is True
    assert result["leakage_detected"] is False
    assert result["oracle_metadata_leakage"] is False


def test_editing_gold_file_after_legal_surface_is_not_leakage():
    rows = [
        {
            "type": "step",
            "action_name": "search_repo",
            "action_input": {"query": "amount", "path": "src"},
            "observation": {"matches": [{"file": "src/summarizer.py", "line": 7, "text": "def total_amount(csv_text):"}]},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/summarizer.py"},
            "observation": {"content": "def total_amount(csv_text):\n    return 0\n"},
        },
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {"file_path": "src/summarizer.py", "old_text": "return 0", "new_text": "return 1"},
            "observation": {"status": "success"},
        },
    ]

    result = leakage_detected(rows, ["src/summarizer.py"], ["total_amount"])

    assert result["gold_identifier_visible"] is True
    assert result["leakage_detected"] is False
    assert result["oracle_metadata_leakage"] is False


def test_reading_public_test_import_surfaces_source_module_for_later_read_and_edit():
    rows = [
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "tests/test_pricing.py"},
            "observation": {"content": "from pricing import PriceService\n\ndef test_cache():\n    assert PriceService({}).cache == {}\n"},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/pricing.py"},
            "observation": {"content": "class PriceService:\n    pass\n"},
        },
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {"file_path": "src/pricing.py", "old_text": "pass", "new_text": "return None"},
            "observation": {"status": "success"},
        },
    ]

    result = leakage_detected(rows, ["src/pricing.py"], ["get_price"])

    assert result["leakage_detected"] is False
    assert result["oracle_metadata_leakage"] is False
    assert result["forbidden_file_access"] is False


def test_simple_import_forms_surface_source_modules():
    rows = [
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "tests/test_imports.py"},
            "observation": {
                "content": "\n".join(
                    [
                        "import pricing",
                        "import package.module as mod",
                        "from another.service import Foo",
                    ]
                )
            },
        },
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {"file_path": "src/package/module.py", "old_text": "old", "new_text": "new"},
            "observation": {"status": "success"},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/another/service.py"},
            "observation": {"content": "class Foo:\n    pass\n"},
        },
    ]

    result = leakage_detected(rows, ["src/package/module.py", "src/another/service.py"], ["Foo"])

    assert result["leakage_detected"] is False
    assert result["oracle_metadata_leakage"] is False


def test_editing_unsurfaced_gold_file_is_oracle_leakage():
    rows = [
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {"file_path": "src/summarizer.py", "old_text": "return 0", "new_text": "return 1"},
            "observation": {"status": "success"},
        },
    ]

    result = leakage_detected(rows, ["src/summarizer.py"], ["total_amount"])

    assert result["leakage_detected"] is True
    assert result["oracle_metadata_leakage"] is True
    assert result["forbidden_file_access"] is False


def test_broken_patch_syntax_does_not_imply_oracle_leakage():
    rows = [
        {
            "type": "step",
            "action_name": "run_test",
            "action_input": {"command": "python -m pytest tests -q", "phase": "pre_public"},
            "observation": {"stdout": "File \"/tmp/task/src/summarizer.py\", line 11, in total_amount"},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/summarizer.py"},
            "observation": {"content": "def total_amount(csv_text):\n    return 0\n"},
        },
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {
                "file_path": "src/summarizer.py",
                "old_text": "return 0",
                "new_text": "if True:\nreturn 1",
            },
            "observation": {"status": "success"},
        },
        {
            "type": "step",
            "action_name": "run_test",
            "action_input": {"command": "python -m pytest tests -q", "phase": "final_public"},
            "observation": {"stdout": "IndentationError: expected an indented block"},
        },
    ]

    result = leakage_detected(rows, ["src/summarizer.py"], ["total_amount"])

    assert result["gold_identifier_visible"] is True
    assert result["leakage_detected"] is False
    assert result["oracle_metadata_leakage"] is False


def test_reading_unsurfaced_gold_file_is_oracle_leakage():
    rows = [
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/config_loader.py"},
            "observation": {"content": "def load_config(path):\n    return {}\n"},
        }
    ]

    result = leakage_detected(rows, ["src/config_loader.py"], ["load_config"])

    assert result["leakage_detected"] is True
    assert result["oracle_metadata_leakage"] is True
    assert result["forbidden_file_access"] is False
    assert result["gold_identifier_visible"] is True


def test_apply_gold_patch_is_oracle_leakage_for_non_gold_policy():
    rows = [
        {
            "type": "step",
            "action_name": "apply_gold_patch",
            "action_input": {},
            "observation": {"status": "success"},
        }
    ]

    result = leakage_detected(rows, ["src/config_loader.py"], ["load_config"])

    assert result["leakage_detected"] is True
    assert result["oracle_metadata_leakage"] is True


def test_rollout_detects_regression_when_bad_patch_breaks_previously_passing_public_test(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_002").resolve(),
        policy=BlindBadPatchPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=3,
        run_hidden=False,
    )

    reward = result["reward"]
    assert reward["pre_public_pass_count"] >= 1
    assert reward["pre_public_fail_count"] >= 1
    assert reward["post_public_pass_count"] < reward["pre_public_pass_count"]
    assert reward["regression"] is True


def test_rollout_reward_contains_leakage_fields(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=GoldPatchPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=4,
        run_hidden=False,
    )

    reward = result["reward"]
    assert "leakage_detected" in reward
    assert "forbidden_file_access" in reward
    assert isinstance(reward["leaked_gold_files"], list)
    json.dumps(result)
