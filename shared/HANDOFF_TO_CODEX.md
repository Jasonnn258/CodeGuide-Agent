# Handoff to Codex (2026-06-28)

## What changed
- Created `claude` branch from `main` (d47a5b9)
- Converted 6 legacy per-phase rollout export scripts to thin wrappers around `run_bounded_rollout_export.py`
  - Each went from ~180-200 lines to 12 lines
  - Old scripts were standalone duplicates of the unified runner
  - Now delegate all logic to `run_bounded_rollout_export.py`
- Added `scripts/__init__.py` to support package imports
- Created shared workspace coordination files: PLAN.md, AGENT_STATE.md, EXECUTION_LOG.md
- Updated CODEX_REVIEW.md to reflect current P1 milestone state

## Verification
- `make test`: 198 passed
- `make audit`: PASS
- `make scale-report`: 100 active tasks, 100 SFT, 169 preference, 64 hard preference
- `make p61-check`: PASS
- `make clean-check`: PASS
- `python -m compileall codeguide_agent`: PASS

## Known limitations
- Legacy scripts are now thin wrappers; old standalone logic is fully replaced
- Hardcoded baseline counts from old scripts are replaced by filesystem-based counting in unified runner

## Suggested next review
- Verify thin wrappers correctly delegate to unified runner (import path, arg passthrough)
- Check that the idempotent `p61_succeeded` logic in `run_bounded_rollout_export.py` is sound
- Confirm no external callers depend on the old per-phase script CLI interface beyond the Makefile
