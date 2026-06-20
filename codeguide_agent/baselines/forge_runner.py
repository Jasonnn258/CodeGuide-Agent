from __future__ import annotations

from pathlib import Path

from codeguide_agent.runtime.agent import AgentConfig, EventLog, ForgeAgent, Task


def run_forge_baseline(
    repo_path: str | Path,
    task_id: str,
    description: str,
    public_test_cmd: str,
    hidden_test_cmd: str,
    trajectory_path: str | Path,
    timeout: int = 30,
) -> dict[str, object]:
    task = Task(
        task_id=task_id,
        repo_path=str(repo_path),
        description=description,
        public_test_cmd=public_test_cmd,
        hidden_test_cmd=hidden_test_cmd,
    )
    log = EventLog(trajectory_path, task_id=task_id)
    result = ForgeAgent(AgentConfig(test_timeout=timeout)).run(task, log)
    return result.to_dict()
