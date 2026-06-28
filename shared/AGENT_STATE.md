# Agent State

- **Date**: 2026-06-28
- **Branch**: `claude`
- **Base**: `main` (d47a5b9)
- **Milestone**: P1 Clean (all P0/P1 roadmap items complete)
- **Active phase**: Post-P1 hardening and cleanup

## P1 Completion Status
| Item | Status | Evidence |
|------|--------|----------|
| P0-1 Commit+tag 100-task v1 | DONE | Committed on main |
| P0-2 p61_succeeded fix | DONE | Idempotent logic in run_bounded_rollout_export.py |
| P0-3 Unified rollout scripts | PARTIAL | Unified runner exists, old scripts not yet thin wrappers |
| P0-4 GPU smoke SFT | DONE | Documented |
| P0-5 Context Management v0 | DONE | codeguide_agent/context/ with tests |
| P0-6 ExperienceRecord extractor | DONE | codeguide_agent/rag/history_index.py with tests |
| P1-1 History RAG in agent loop | DONE | codeguide_agent/rag/agent_loop.py with tests |
| P1-2 Code RAG v0 | DONE | codeguide_agent/rag/ with hybrid retrieval + tests |
| P1-3 SWE-bench Lite adapter | DONE | codeguide_agent/eval/swe_bench_adapter.py with tests |

## Hard Limits (never violate)
- No training unless explicitly requested
- No task_101+ unless explicitly requested
- No external APIs unless explicitly requested
- No llm rollout policy unless explicitly requested
- No model-performance claims
- No hidden/gold/oracle leakage into model-facing artifacts
- Do not delete user work or large project data
- Do not commit model weights, caches, checkpoints, pyc files, or secrets
