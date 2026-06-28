# Plan: P1 Clean Milestone → Next Steps

## Current State (2026-06-28)

- Branch: `claude` (created from `main`)
- Tests: 198 passed
- Audit: PASS
- Scale: 100 tasks, 100 SFT, 169 preference, 64 hard preference
- P0/P1 roadmap items: ALL complete
- Wrapper conversion: 6 legacy scripts → thin wrappers (committed)
- Wrapper delegation smoke test: scripts/test_wrapper_delegation.py (6/6 PASS)

## Verification baseline (all PASS)
- `make test`: 198 passed
- `make audit`: PASS
- `make scale-report`: 100/100/169/64
- `make p61-check`: PASS
- `make clean-check`: PASS
- `python -m compileall codeguide_agent`: PASS

## Planned Work (this cycle)

### 1. Codex review fixes (post-P1 hardening)
- Add smoke test for wrapper delegation (scripts/test_wrapper_delegation.py)
- Update AGENT_STATE.md: P0-3 PARTIAL → DONE
- Update PLAN.md to reflect completed wrapper conversion
- Update HANDOFF_TO_CODEX.md with fix details

### 2. Validation and commit
- Run wrapper delegation smoke test plus existing validation suite
- Commit to `claude` branch
- Push to `origin/claude`

## Blocked / Deferred
- P2-1 API Docs RAG: requires external doc fetching (blocked by hard limit)
- P2-2 SWE-smith task generator: would create task_101+ (blocked by hard limit)
- P2-3 Formal training: blocked by hard limit
- Data expansion beyond 100 tasks: blocked by hard limit
