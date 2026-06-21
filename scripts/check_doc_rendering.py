#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

CHECK_FILES = [
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("docs/PROJECT_STORY.md"),
    Path("docs/RESUME_BULLETS.md"),
    Path("docs/INTERVIEW_PROJECT_BRIEF.md"),
]

def main() -> None:
    failed = False
    for path in CHECK_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "\\n" in text:
            print(f"FAIL literal backslash-n found in {path}")
            failed = True
        long_lines = [i + 1 for i, line in enumerate(text.splitlines()) if len(line) > 500]
        if long_lines:
            print(f"WARN very long markdown lines in {path}: {long_lines[:10]}")
    if failed:
        raise SystemExit(1)
    print("PASS: markdown docs rendering check")

if __name__ == "__main__":
    main()
