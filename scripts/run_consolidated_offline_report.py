#!/usr/bin/env python3
"""P1.7 Consolidated Offline Eval/Ablation Report — single local command.

Usage:
    python scripts/run_consolidated_offline_report.py              # Markdown to stdout
    python scripts/run_consolidated_offline_report.py --json -     # JSON to stdout
    python scripts/run_consolidated_offline_report.py --json out.json --markdown out.md
    python scripts/run_consolidated_offline_report.py --root data/mini_repo_debug

Consolidates the P1.5 eval harness, P1.6 dataset quality diagnostics, and the
three RAG offline ablation outputs (history RAG, code RAG localization, agent
loop ablation) into a single local offline report. JSON + Markdown.

All operations are local. No training, no external APIs, no LLM calls, no
hidden/gold/oracle leakage in the report output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.eval.consolidated_report import (
    build_consolidated_report,
    format_json,
    format_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="P1.7 Consolidated Offline Report")
    parser.add_argument("--json", dest="json_out", default=None, metavar="PATH",
                        help="Write JSON to PATH (- for stdout)")
    parser.add_argument("--markdown", dest="md_out", default=None, metavar="PATH",
                        help="Write Markdown to PATH (- for stdout)")
    parser.add_argument("--root", default="data/mini_repo_debug",
                        help="Mini-Repo-Debug root directory")
    args = parser.parse_args()

    if args.json_out is None and args.md_out is None:
        args.md_out = "-"

    report = build_consolidated_report(root=Path(args.root))

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
