from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from codeguide_agent.runtime.agent.event_log import EventLog
from codeguide_agent.runtime.agent.types import Action, ActionType, RunResult, RunStatus, Task, ToolCall
from codeguide_agent.runtime.tools import (
    FileReadTool,
    FileWriteTool,
    GitDiffTool,
    SearchTool,
    ShellTool,
    TestTool,
    ToolRegistry,
)


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 8
    test_timeout: int = 30
    use_gold_patch_when_mocked: bool = True


def default_registry(repo_path: str | Path, timeout: int = 30) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(FileReadTool(repo_path))
    registry.register(FileWriteTool(repo_path))
    registry.register(SearchTool(repo_path))
    registry.register(ShellTool(repo_path, default_timeout=timeout))
    registry.register(TestTool(repo_path, default_timeout=timeout))
    registry.register(GitDiffTool(repo_path))
    return registry


class ForgeAgent:
    """Small forge-style loop used as a research runtime boundary."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig()

    def run(self, task: Task, log: EventLog) -> RunResult:
        repo_path = Path(task.repo_path)
        registry = default_registry(repo_path, self.config.test_timeout)
        log.task_start(task)

        issue = repo_path / (task.issue_path or "issue.md")
        if issue.exists():
            action = Action(ActionType.TOOL_CALL, "Read the issue.", ToolCall("file_read", {"path": issue.name}))
            log.action(1, action)
            log.observation(1, registry.execute("file_read", {"path": issue.name}).to_observation("file_read"))

        step = 2
        public_cmd = task.public_test_cmd or "python -m pytest tests"
        action = Action(ActionType.TOOL_CALL, "Run the public tests before editing.", ToolCall("test", {"cmd": public_cmd}))
        log.action(step, action)
        log.observation(step, registry.execute("test", {"cmd": public_cmd}).to_observation("test"))

        gold_patch = repo_path / "gold.patch"
        if self.config.use_gold_patch_when_mocked and gold_patch.exists():
            step += 1
            action = Action(ActionType.TOOL_CALL, "Apply the local gold patch for deterministic baseline repair.", ToolCall("shell", {"cmd": "git apply gold.patch"}))
            log.action(step, action)
            log.observation(step, registry.execute("shell", {"cmd": "git apply gold.patch", "timeout": 10}).to_observation("shell"))

        step += 1
        action = Action(ActionType.TOOL_CALL, "Inspect the resulting patch.", ToolCall("git_diff", {}))
        log.action(step, action)
        diff_observation = registry.execute("git_diff", {}).to_observation("git_diff")
        log.observation(step, diff_observation)

        patch = _git_diff(repo_path)
        summary = "forge-style deterministic run complete"
        log.complete(step, summary)
        return RunResult(
            task_id=task.task_id,
            status=RunStatus.SUCCESS,
            summary=summary,
            steps_taken=step,
            patch=patch,
            trajectory_path=str(log.path),
        )


def _git_diff(repo_path: Path) -> str:
    completed = subprocess.run(
        "git diff -- .",
        cwd=repo_path,
        shell=True,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    return (completed.stdout or "") + (completed.stderr or "")
