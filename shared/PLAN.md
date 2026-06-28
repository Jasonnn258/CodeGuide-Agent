# Plan: P1 Clean Milestone → Next Steps

## Current State (2026-06-28)

- Branch: `claude` (created from `main`)
- Tests: 198 passed
- Audit: PASS
- Scale: 100 tasks, 100 SFT, 169 preference, 64 hard preference
- P0/P1 roadmap items: ALL complete

## Verification baseline (all PASS)
- `make test`: 198 passed
- `make audit`: PASS
- `make scale-report`: 100/100/169/64
- `make p61-check`: PASS
- `make clean-check`: PASS
- `python -m compileall codeguide_agent`: PASS

## Planned Work (this cycle)

### 1. Shared workspace initialization
- Create AGENT_STATE.md, EXECUTION_LOG.md, HANDOFF_TO_CODEX.md

### 2. Legacy per-phase rollout script cleanup (P0-3 completion)
- The roadmap P0-3 says old phase scripts should be thin wrappers around `run_bounded_rollout_export.py`
- Current state: old scripts (p34_rollout_export_021_025.py, etc.) are still standalone ~180-200 line duplicates
- Convert them to thin wrappers that delegate to `run_bounded_rollout_export.py`

### 3. Update stale CODEX_REVIEW.md
- Current review references P3C work that is already completed
- Update to reflect current P1 milestone state

### 4. Validation and commit
- Run full validation suite after changes
- Commit to `claude` branch
- Push to `origin/claude`

## Blocked / Deferred
- P2-1 API Docs RAG: requires external doc fetching (blocked by hard limit)
- P2-2 SWE-smith task generator: would create task_101+ (blocked by hard limit)
- P2-3 Formal training: blocked by hard limit
- Data expansion beyond 100 tasks: blocked by hard limit
