Verdict: request changes

Must-fix
- Add direct validation for the changed wrapper entry points. The handoff lists `make test`, `make audit`, `make scale-report`, `make p61-check`, `make clean-check`, and compile checks, but I found no test/check reference to `scripts/p34_rollout_export_021_025.py` through `scripts/p61_rollout_export_061_100.py` or `scripts/run_bounded_rollout_export.py`. `compileall` proves syntax/import parsing, not that each wrapper passes the intended `--task-start`, `--task-end`, and `--phase` values to the unified runner. A safe smoke can monkeypatch `scripts.run_bounded_rollout_export.main` and run each wrapper without launching rollouts.
- Update stale shared-state text before treating this as ready. `shared/AGENT_STATE.md` still marks `P0-3 Unified rollout scripts` as `PARTIAL` and says old scripts are not yet thin wrappers, while this branch changes exactly that. `shared/PLAN.md` also describes the wrapper conversion as planned/current work even though the commit already performed it.
- Do not claim "no behavioral changes" for this refactor unless it is explicitly validated. The wrappers now inherit the unified runner's filesystem-based counting, idempotent success threshold, timeout default, summary shape, and CLI behavior. That is probably intended, but it is still behavior replacement for the legacy scripts.

Should-fix
- Branch safety is good: current branch is `claude`, `main` and `origin/main` remain at `d47a5b9`, and the branch diff is isolated to wrapper scripts plus shared coordination files.
- Main appears untouched. Keep all follow-up fixes on `claude`.
- The next milestone is reasonable if scoped as post-P1 cleanup hardening: finish wrapper validation, fix shared docs, then decide whether P2 work needs explicit approval because the current plan correctly flags external API fetching, task_101+, formal training, and LLM rollout work as hard limits.
- I do not see training-performance or SWE-bench benchmark overclaims in the handoff. The claims are mostly data/test counts and adapter-readiness statements, but keep "GPU smoke SFT" and "SWE-bench Lite adapter DONE" framed as smoke/adapter readiness, not model quality or benchmark performance.
- Validation is broad but not sufficient for this diff until the changed wrapper entry points have a direct smoke. After that, the existing `make test`, `make audit`, `make scale-report`, `make p61-check`, `make clean-check`, and compile checks are adequate for a cleanup-only branch.

Suggested next `/goal` for Claude Code
- `/goal Finish the P1-clean wrapper refactor review fixes on branch claude: add a non-destructive smoke test or check proving each legacy rollout wrapper delegates to run_bounded_rollout_export.py with the correct phase/task arguments, update shared state/plan text to match the completed refactor, rerun targeted wrapper validation plus the existing clean/audit/test checks, and hand off the exact results without training or benchmark-performance claims.`
