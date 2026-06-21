#!/usr/bin/env bash
set -euo pipefail

HOLD_DIR="/tmp/codeguide_trajectories_hold_$$"
RESTORED=0

cleanup() {
  if [ "$RESTORED" -eq 0 ] && [ -d "$HOLD_DIR" ] && [ ! -d data/mini_repo_debug/trajectories ]; then
    mv "$HOLD_DIR" data/mini_repo_debug/trajectories
  fi
}
trap cleanup EXIT

if [ -d data/mini_repo_debug/trajectories ]; then
  mv data/mini_repo_debug/trajectories "$HOLD_DIR"
fi

python -m codeguide_agent.testing.simple_pytest tests -q

if [ -d "$HOLD_DIR" ]; then
  mv "$HOLD_DIR" data/mini_repo_debug/trajectories
  RESTORED=1
fi

echo "PASS: tests do not depend on generated trajectories."
