#!/usr/bin/env python3
"""P1.5 Eval Harness Report — unified local offline status check.

Usage:
    python scripts/run_eval_harness_report.py              # print Markdown to stdout
    python scripts/run_eval_harness_report.py --json -     # print JSON to stdout
    python scripts/run_eval_harness_report.py --json out.json --markdown out.md

All operations are local. No training, external APIs, or LLM calls.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.eval.harness_reporter import build_report, format_json, format_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="P1.5 Eval Harness Report")
    parser.add_argument("--json", dest="json_out", default=None, metavar="PATH",
                        help="Write JSON to PATH (- for stdout)")
    parser.add_argument("--markdown", dest="md_out", default=None, metavar="PATH",
                        help="Write Markdown to PATH (- for stdout)")
    parser.add_argument("--root", default="data/mini_repo_debug",
                        help="Mini-Repo-Debug root directory")
    args = parser.parse_args()

    # Default: Markdown to stdout if neither flag given
    if args.json_out is None and args.md_out is None:
        args.md_out = "-"

    report = build_report(root=Path(args.root))

    json_text = format_json(report)
    md_text = format_markdown(report)

    if args.json_out == "-":
        sys.stdout.write(json_text)
    elif args.json_out:
        Path(args.json_out).write_text(json_text, encoding="utf-8")

    if args.md_out == "-":
        sys.stdout.write(md_text)
    elif args.md_out:
        Path(args.md_out).write_text(md_text, encoding="utf-8")

    return 0 if report.overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
