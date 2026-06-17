#!/usr/bin/env bash
set -euo pipefail

TEMP_ROOT="${TEMP_ROOT:-/tmp/codeguide_eval}"
HIDDEN_ARGS=""

if [[ "${RUN_HIDDEN:-0}" == "1" ]]; then
  HIDDEN_ARGS="--run-hidden"
fi

python -m codeguide_agent.eval.run_eval \
  --root data/mini_repo_debug \
  --mode noop \
  --temp-root "$TEMP_ROOT" \
  $HIDDEN_ARGS

python -m codeguide_agent.eval.run_eval \
  --root data/mini_repo_debug \
  --mode gold \
  --temp-root "$TEMP_ROOT" \
  $HIDDEN_ARGS
