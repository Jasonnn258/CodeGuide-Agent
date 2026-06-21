#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

CHECK_FILES = [
    Path("AGENTS.md"),
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("docs/PHASE2_ROLLOUT_PLAN.md"),
    Path("docs/PROJECT_STORY.md"),
    Path("docs/RESUME_BULLETS.md"),
    Path("docs/INTERVIEW_PROJECT_BRIEF.md"),
    Path("docs/CANONICAL_TRAINING_DATA_PIPELINE.md"),
]

LEGACY_COMMANDS = [
    "python -m codeguide_agent.data_builders.build_sft",
    "python -m codeguide_agent.training_data.build_sft_from_trajectories",
]

def main() -> None:
    failed = False
    for path in CHECK_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for cmd in LEGACY_COMMANDS:
            if cmd in text:
                print(f"FAIL legacy SFT command in public doc: {path}: {cmd}")
                failed = True
    if failed:
        raise SystemExit(1)
    print("PASS: canonical training pipeline check")

if __name__ == "__main__":
    main()
