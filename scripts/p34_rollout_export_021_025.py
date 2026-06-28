#!/usr/bin/env python3
"""Thin wrapper around run_bounded_rollout_export.py for Phase P34 (tasks 021-025)."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.run_bounded_rollout_export as _runner

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--task-start", "21", "--task-end", "25", "--phase", "p34"]
    raise SystemExit(_runner.main())
