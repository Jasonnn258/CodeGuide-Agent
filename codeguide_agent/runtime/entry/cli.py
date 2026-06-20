from __future__ import annotations

import argparse
from pathlib import Path

from codeguide_agent.runtime.agent import EventLog, ForgeAgent, Task


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CodeGuide forge-style runtime on a local repo.")
    parser.add_argument("repo")
    parser.add_argument("--task-id", default="manual")
    parser.add_argument("--description", default="Inspect and repair the repository.")
    parser.add_argument("--trajectory", default="data/mini_repo_debug/trajectories/manual.jsonl")
    args = parser.parse_args()

    task = Task(task_id=args.task_id, repo_path=args.repo, description=args.description)
    log = EventLog(Path(args.trajectory), task.task_id)
    result = ForgeAgent().run(task, log)
    print(result.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
