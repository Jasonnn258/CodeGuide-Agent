from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Aider baseline runner placeholder.")
    parser.add_argument("--task-repo", required=True, help="Mini-Repo-Debug task repository")
    parser.add_argument("--model", default="aider-default", help="Aider model name for future integration")
    parser.add_argument("--dry-run", action="store_true", help="Print planned command without running Aider")
    args = parser.parse_args()
    print(
        "TODO: integrate Aider as a baseline/teacher. "
        f"task_repo={args.task_repo} model={args.model} dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
