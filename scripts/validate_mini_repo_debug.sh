#!/usr/bin/env bash
set -euo pipefail

python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
