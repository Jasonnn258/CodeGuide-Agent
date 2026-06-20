from __future__ import annotations

from pathlib import Path
from typing import Any
import ast
import re
import shutil
import subprocess

from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.evaluators.localization_eval import localization_process_metrics, patch_localization_metrics
from codeguide_agent.eval.run_eval import compute_repo_checksum, copy_task_to_temp
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.reward.hacking_checks import leakage_detected
from codeguide_agent.rollout.actions import Action, parse_action
from codeguide_agent.rollout.policy import BasePolicy
from codeguide_agent.rollout.state import RolloutState
from codeguide_agent.tools.edit_file import edit_file
from codeguide_agent.tools.git_diff import git_diff
from codeguide_agent.tools.read_file import read_file
from codeguide_agent.tools.repo_tree import repo_tree
from codeguide_agent.tools.rollback import rollback
from codeguide_agent.tools.run_test import run_test
from codeguide_agent.tools.search_repo import search_repo
from codeguide_agent.trajectory.logger import TrajectoryLogger


class RolloutCollector:
    def __init__(self, trajectories_dir: str | Path = "data/mini_repo_debug/trajectories", timeout: int = 30, keep_temp: bool = False):
        self.trajectories_dir = Path(trajectories_dir)
        self.timeout = timeout
        self.keep_temp = keep_temp

    def collect(
        self,
        task: str | Path,
        policy: BasePolicy,
        temp_root: str | Path,
        max_steps: int,
        run_hidden: bool = False,
        keep_temp: bool | None = None,
    ) -> dict[str, Any]:
        original_task = Path(task).resolve()
        metadata = load_metadata(original_task)
        task_id = metadata["task_id"]
        issue_text = (original_task / metadata.get("issue_path", "issue.md")).read_text(encoding="utf-8")
        before_checksum = compute_repo_checksum(original_task)
        temp_repo = copy_task_to_temp(original_task, temp_root, task_id)
        _ensure_git_repo(temp_repo, timeout=self.timeout)
        should_keep_temp = self.keep_temp if keep_temp is None else keep_temp
        trajectory_id = f"{task_id}_{policy.name}"
        trajectory_path = self.trajectories_dir / f"{trajectory_id}.jsonl"
        if trajectory_path.exists():
            trajectory_path.unlink()
        logger = TrajectoryLogger(trajectory_path, task_id, trajectory_id, model=f"rollout_{policy.name}")
        state = RolloutState(task_id=task_id, repo_path=temp_repo, issue_text=issue_text, step_id=0, max_steps=max_steps)
        public_result: dict[str, Any] | None = None
        pre_public_result: dict[str, Any] | None = None
        hidden_result: dict[str, Any] | None = None
        final_diff = ""

        try:
            pre_public_result = run_test(temp_repo, metadata["public_test_cmd"], timeout=self.timeout)
            state.observations.append(
                logger.log_step(
                    "run_test",
                    {"command": metadata["public_test_cmd"], "phase": "pre_public"},
                    pre_public_result,
                    "Run pre-patch public verifier for regression baseline.",
                )
            )
            seen_calls: set[tuple[str, str]] = set()
            while not state.done and state.step_id < max_steps:
                raw_action = policy.next_action(state)
                parsed = parse_action(raw_action.to_dict() if isinstance(raw_action, Action) else raw_action)
                if not parsed.ok or parsed.action is None:
                    self._record_invalid_action(state, parsed.error_type)
                    observation = {"tool_name": "action_parser", "status": "error", "error": parsed.error}
                    step = logger.log_step("invalid_action", {}, observation, "")
                    state.observations.append(step)
                    state.step_id += 1
                    if parsed.error_type == "unknown_tool":
                        state.stop_reason = "unknown_tool"
                        state.done = True
                    continue

                action = self._resolve_placeholders(parsed.action, metadata)
                call_key = (action.action_name, repr(sorted(action.action_input.items())))
                if call_key in seen_calls:
                    state.duplicate_tool_count += 1
                seen_calls.add(call_key)

                violation = self._repair_loop_violation(policy, action, state)
                if violation:
                    self._record_invalid_action(state, "repair_loop")
                    state.repair_loop_violation_count += 1
                    observation = violation
                else:
                    observation = self._execute_action(action, state)
                if observation.get("status") == "timeout":
                    state.tool_timeout_count += 1
                self._update_state_from_action(state, action, observation)
                step = logger.log_step(action.action_name, action.action_input, observation, action.thought)
                state.observations.append(step)
                state.step_id += 1
                if policy.name == "llm" and action.action_name == "edit_file" and observation.get("status") == "success":
                    auto_result = run_test(temp_repo, metadata["public_test_cmd"], timeout=self.timeout)
                    state.auto_public_test_after_edit_count += 1
                    state.tests_run.append(metadata["public_test_cmd"])
                    state.final_test_ran = True
                    state._requires_post_edit_check = False
                    auto_step = logger.log_step(
                        "run_test",
                        {"command": metadata["public_test_cmd"], "phase": "auto_public_after_edit"},
                        auto_result,
                        "Automatically run public verifier after successful LLM edit.",
                    )
                    state.observations.append(auto_step)
                    if auto_result.get("exit_code") == 0:
                        state.done = True
                        state.stop_reason = "test_pass"

                if action.action_name == "stop":
                    state.done = True
                    state.stop_reason = action.action_input.get("reason", "policy_stop")
                elif action.action_name == "run_test" and observation.get("exit_code") == 0:
                    state.done = True
                    state.stop_reason = "test_pass"
                elif observation.get("status") == "error" and action.action_name == "apply_gold_patch":
                    state.done = True
                    state.stop_reason = "unrecoverable_error"

            if not state.done:
                state.stop_reason = "max_steps"

            if not any("tests" in command for command in state.tests_run):
                public_result = run_test(temp_repo, metadata["public_test_cmd"], timeout=self.timeout)
                step = logger.log_step("run_test", {"command": metadata["public_test_cmd"], "phase": "final_public"}, public_result, "Run final public verifier.")
                state.observations.append(step)
                state.tests_run.append(metadata["public_test_cmd"])
                state.final_test_ran = True
            else:
                public_result = self._last_test_result(state)

            if run_hidden:
                hidden_result = run_test(temp_repo, metadata["hidden_test_cmd"], timeout=self.timeout)
                step = logger.log_step("run_test", {"command": metadata["hidden_test_cmd"], "phase": "final_hidden"}, hidden_result, "Run final hidden verifier.")
                state.observations.append(step)
                state.tests_run.append(metadata["hidden_test_cmd"])

            diff_result = git_diff(temp_repo)
            final_diff = diff_result.get("diff", "")
            if policy.name == "gold" and not final_diff:
                final_diff = (temp_repo / "gold.patch").read_text(encoding="utf-8")
            state.observations.append(logger.log_step("git_diff", {"phase": "final"}, {**diff_result, "diff": final_diff}, "Collect final rollout diff."))
            state.final_diff_collected = True

            pre_counts = public_test_counts(pre_public_result)
            post_counts = public_test_counts(public_result)
            regression = post_counts["pass_count"] < pre_counts["pass_count"]
            patch_localization = patch_localization_metrics(
                final_diff,
                temp_repo,
                metadata.get("gold_files", []),
                metadata.get("gold_functions", []),
            )
            process_localization = localization_process_metrics(
                state.observations,
                temp_repo,
                metadata.get("gold_files", []),
                metadata.get("gold_functions", []),
            )
            leakage = leakage_detected(
                _agent_visible_observations(state.observations),
                metadata.get("gold_files", []),
                metadata.get("gold_functions", []),
            )
            reward = calculate_reward(
                public_result,
                hidden_result,
                final_diff,
                regression=regression,
                gold_files=metadata.get("gold_files", []),
                suspicious_files=list(dict.fromkeys(metadata.get("gold_files", []) + state.opened_files)),
                action_stats=state.action_stats(),
            )
            reward.update(
                {
                    **patch_localization,
                    **process_localization,
                    **leakage,
                    "pre_public_pass_count": pre_counts["pass_count"],
                    "pre_public_fail_count": pre_counts["fail_count"],
                    "post_public_pass_count": post_counts["pass_count"],
                    "post_public_fail_count": post_counts["fail_count"],
                    "regression": regression,
                    "syntax_error": state.syntax_error,
                    "syntax_error_files": state.syntax_error_files,
                    "repeated_edit_count": state.repeated_edit_count,
                    "edit_retry_count": state.edit_retry_count,
                    "repair_loop_violation_count": state.repair_loop_violation_count,
                    "auto_public_test_after_edit_count": state.auto_public_test_after_edit_count,
                    "incomplete_stop": state.incomplete_stop,
                    "final_test_ran": state.final_test_ran,
                    "final_diff_collected": state.final_diff_collected,
                }
            )
            final_status = "success" if reward["public_pass"] and (reward["hidden_pass"] or not run_hidden) else "fail"
            logger.log_final(final_diff, reward, final_status)
        finally:
            if not should_keep_temp and temp_repo.exists():
                shutil.rmtree(temp_repo)

        after_checksum = compute_repo_checksum(original_task)
        original_unchanged = before_checksum == after_checksum
        return {
            "task_id": task_id,
            "policy": policy.name,
            "trajectory_path": str(logger.path),
            "steps": logger.step_count,
            "observations": state.observations,
            "reward": reward,
            "success": final_status == "success",
            "done": state.done,
            "stop_reason": state.stop_reason,
            "invalid_action_count": state.invalid_action_count,
            "invalid_json_count": state.invalid_json_count,
            "unknown_tool_count": state.unknown_tool_count,
            "tool_timeout_count": state.tool_timeout_count,
            "duplicate_tool_count": state.duplicate_tool_count,
            "repeated_edit_count": state.repeated_edit_count,
            "edit_retry_count": state.edit_retry_count,
            "repair_loop_violation_count": state.repair_loop_violation_count,
            "auto_public_test_after_edit_count": state.auto_public_test_after_edit_count,
            "syntax_error": state.syntax_error,
            "syntax_error_files": state.syntax_error_files,
            "incomplete_stop": state.incomplete_stop,
            "final_test_ran": state.final_test_ran,
            "final_diff_collected": state.final_diff_collected,
            "opened_files": state.opened_files,
            "searched_queries": state.searched_queries,
            "edited_files": state.edited_files,
            "tests_run": state.tests_run,
            "original_repo_unchanged": original_unchanged,
            "original_checksum_before": before_checksum,
            "original_checksum_after": after_checksum,
            "temp_repo_path": str(temp_repo),
            **_policy_metadata(policy),
        }

    def _execute_action(self, action: Action, state: RolloutState) -> dict[str, Any]:
        name = action.action_name
        data = action.action_input
        if name == "repo_tree":
            return repo_tree(state.repo_path, max_depth=int(data.get("max_depth", 4)))
        if name == "search_repo":
            return search_repo(state.repo_path, data["query"], path=data.get("path", "."), file_glob=data.get("file_glob"), max_matches=int(data.get("max_matches", 50)))
        if name == "read_file":
            return read_file(state.repo_path, data["file_path"], start_line=data.get("start_line"), end_line=data.get("end_line"))
        if name == "edit_file":
            return edit_file(state.repo_path, data["file_path"], data["old_text"], data["new_text"], expected_replacements=int(data.get("expected_replacements", 1)))
        if name == "run_test":
            return run_test(state.repo_path, data["command"], timeout=int(data.get("timeout", self.timeout)))
        if name == "git_diff":
            return git_diff(state.repo_path)
        if name == "rollback":
            return rollback(state.repo_path)
        if name == "apply_gold_patch":
            proc = subprocess.run(["git", "apply", "gold.patch"], cwd=state.repo_path, text=True, capture_output=True)
            return {"tool_name": "apply_gold_patch", "status": "success" if proc.returncode == 0 else "error", "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        if name == "stop":
            return {"tool_name": "stop", "status": "success", "reason": data.get("reason", "")}
        return {"tool_name": name, "status": "error", "error": "unknown action"}

    def _update_state_from_action(self, state: RolloutState, action: Action, observation: dict[str, Any]) -> None:
        if observation.get("repair_loop_violation"):
            return
        if action.action_name == "search_repo":
            state.searched_queries.append(action.action_input["query"])
        elif action.action_name == "read_file" and observation.get("status") == "success":
            file_path = observation.get("file", action.action_input["file_path"])
            if file_path not in state.opened_files:
                state.opened_files.append(file_path)
            state._requires_read_after_failed_edit = False
            state._requires_post_edit_check = False
        elif action.action_name == "edit_file" and observation.get("status") == "success":
            file_path = observation.get("file", action.action_input["file_path"])
            if file_path not in state.edited_files:
                state.edited_files.append(file_path)
            state._last_edit_status = "success"
            state._last_edit_file = file_path
            state._requires_post_edit_check = True
            state._requires_read_after_failed_edit = False
            self._record_python_syntax_status(state, file_path)
        elif action.action_name == "edit_file" and observation.get("status") == "error":
            state._last_edit_status = "error"
            state._last_edit_file = action.action_input.get("file_path", "")
            state._requires_read_after_failed_edit = True
        elif action.action_name == "apply_gold_patch" and observation.get("status") == "success":
            state.edited_files.append("gold.patch")
        elif action.action_name == "run_test":
            state.tests_run.append(action.action_input["command"])
            if action.action_input.get("phase") != "pre_public":
                state.final_test_ran = True
            state._requires_post_edit_check = False
        elif action.action_name == "git_diff":
            state.final_diff_collected = True
            state._requires_post_edit_check = False
        elif action.action_name == "stop":
            if not (state.final_test_ran and state.final_diff_collected):
                state.incomplete_stop = True

    def _record_invalid_action(self, state: RolloutState, error_type: str | None) -> None:
        state.invalid_action_count += 1
        if error_type == "invalid_json":
            state.invalid_json_count += 1
        elif error_type == "unknown_tool":
            state.unknown_tool_count += 1

    def _resolve_placeholders(self, action: Action, metadata: dict[str, Any]) -> Action:
        if action.action_name == "run_test" and action.action_input.get("command") == "__PUBLIC_TEST__":
            return Action(action.thought, action.action_name, {**action.action_input, "command": metadata["public_test_cmd"]})
        return action

    def _last_test_result(self, state: RolloutState) -> dict[str, Any] | None:
        for row in reversed(state.observations):
            observation = row.get("observation", {})
            if observation.get("tool_name") == "run_test" and row.get("action_input", {}).get("phase") != "pre_public":
                return observation
        return None

    def _repair_loop_violation(self, policy: BasePolicy, action: Action, state: RolloutState) -> dict[str, Any] | None:
        if policy.name != "llm" or action.action_name != "edit_file":
            return None
        file_path = self._normalized_action_file_path(state, action)
        old_text = str(action.action_input.get("old_text", ""))
        edit_key = (file_path, old_text)
        if file_path not in state.opened_files:
            state.edit_retry_count += 1
            return _repair_loop_error(
                file_path,
                "edit_file requires a successful read_file on the target first",
                allowed_next_actions=["read_file"],
                required_next_action="read_file",
            )
        if edit_key in state._seen_edit_keys:
            state.repeated_edit_count += 1
            return _repair_loop_error(
                file_path,
                "repeated file_path + old_text edit rejected",
                allowed_next_actions=["run_test", "read_file", "git_diff"],
            )
        if state._requires_read_after_failed_edit:
            state.edit_retry_count += 1
            return _repair_loop_error(
                file_path,
                "failed edit_file must be followed by read_file before another edit",
                allowed_next_actions=["read_file"],
                required_next_action="read_file",
            )
        if state._requires_post_edit_check:
            state.edit_retry_count += 1
            return _repair_loop_error(
                file_path,
                "successful edit_file must be followed by run_test, read_file, or git_diff before another edit",
                allowed_next_actions=["run_test", "read_file", "git_diff"],
            )
        state._seen_edit_keys.add(edit_key)
        return None

    def _normalized_action_file_path(self, state: RolloutState, action: Action) -> str:
        from codeguide_agent.tools.common import normalize_repo_relative_path

        raw_path = action.action_input.get("file_path", "")
        try:
            normalized = normalize_repo_relative_path(state.repo_path, raw_path)
            action.action_input["file_path"] = normalized
            return normalized
        except Exception:
            return str(raw_path)

    def _record_python_syntax_status(self, state: RolloutState, file_path: str) -> None:
        if not file_path.endswith(".py"):
            return
        target = state.repo_path / file_path
        if not target.exists():
            return
        try:
            ast.parse(target.read_text(encoding="utf-8"))
        except SyntaxError:
            state.syntax_error = True
            if file_path not in state.syntax_error_files:
                state.syntax_error_files.append(file_path)


def public_test_counts(result: dict[str, Any] | None) -> dict[str, int]:
    if not result:
        return {"pass_count": 0, "fail_count": 0}
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    pass_count = _extract_count(text, "passed")
    fail_count = _extract_count(text, "failed")
    if pass_count == 0 and fail_count == 0:
        if result.get("exit_code") == 0:
            pass_count = 1
        else:
            fail_count = 1
    return {"pass_count": pass_count, "fail_count": fail_count}


def _agent_visible_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in observations
        if not (row.get("action_name") == "run_test" and row.get("action_input", {}).get("phase") == "final_hidden")
    ]


def _extract_count(text: str, label: str) -> int:
    matches = re.findall(rf"(\d+)\s+{label}", text)
    return sum(int(value) for value in matches)


def _repair_loop_error(
    file_path: str,
    error: str,
    allowed_next_actions: list[str],
    required_next_action: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": "repair_loop_guard",
        "status": "error",
        "file": file_path,
        "error": error,
        "repair_loop_violation": True,
        "allowed_next_actions": allowed_next_actions,
        "required_next_action": required_next_action or "",
    }


def _policy_metadata(policy: BasePolicy) -> dict[str, Any]:
    metadata = getattr(policy, "metadata", None)
    if not callable(metadata):
        return {}
    data = metadata()
    if not isinstance(data, dict):
        return {}
    return data


def _ensure_git_repo(repo_path: Path, timeout: int) -> None:
    if (repo_path / ".git").exists():
        return
    commands = [
        ["git", "init"],
        ["git", "config", "user.email", "codeguide@example.invalid"],
        ["git", "config", "user.name", "CodeGuide Eval"],
        ["git", "add", "."],
        ["git", "commit", "-m", "baseline"],
    ]
    for command in commands:
        subprocess.run(command, cwd=repo_path, text=True, capture_output=True, timeout=min(timeout, 30), check=False)
