#!/usr/bin/env python3
"""Thin wrapper around run_bounded_rollout_export.py for Phase P55 (tasks 051-060)."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.run_bounded_rollout_export as _runner

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--task-start", "51", "--task-end", "60", "--phase", "p55"]
    raise SystemExit(_runner.main())
