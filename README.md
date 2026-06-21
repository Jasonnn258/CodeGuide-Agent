# CodeGuide-Agent

CodeGuide-Agent is a research-oriented Code Intelligence and Coding Agent
platform. Its first target is verifier-driven repo-level debugging on
Mini-Repo-Debug tasks.

The project is not just a forked coding assistant. The core contribution is the
research stack around coding agents: mini repo datasets, fault localization
evaluation, patch minimality verification, process/outcome reward, trajectory
mining, and future SFT/DPO/GRPO data builders.

## Project Positioning

The main loop is:

```text
Issue + Mini Repo + Failing Tests
→ repo navigation
→ fault localization
→ minimal patch
→ public/hidden test verification
→ trajectory log
→ verifier reward
```

## Runtime Components

CodeGuide-Agent includes a compact forge-style runtime under
`codeguide_agent/runtime/`. It was adapted from an earlier local prototype
available in this workspace as `/Users/yjx/Code/forge-agent`. No license file
is present in that local checkout, so this repository does not claim to be
based on an open-source forge-agent dependency.

The canonical Mini-Repo-Debug rollout path currently uses `RolloutCollector`
and the CodeGuide tool layer under `codeguide_agent/tools/*`. The
`codeguide_agent/runtime/` package is retained as a baseline/demo runtime and
as a reference implementation for these runtime ideas:

- agent loop boundary,
- task/action/observation dataclasses,
- event log JSONL,
- tool registry,
- file/search/shell/test/git tools,
- repo map/context,
- LLM backend router,
- CLI entry surface.

See `NOTICE.md` and `docs/forge_runtime_migration.md`.

## Aider Role

Aider is treated as a strong baseline, teacher, and repo-map/edit-format
reference. It is not the main base of CodeGuide-Agent. This keeps the project
focused on dataset, evaluation, reward, trajectory, and training-data
infrastructure rather than becoming a thin wrapper around an existing pair
programming tool.

See `docs/aider_baseline_teacher_reference.md`.

## Implemented Scope

Implemented components include:

- Mini-Repo-Debug task schema and validator.
- Five handcrafted Python pytest mini repos under `data/mini_repo_debug/repos/`.
- Shared tool layer: `repo_tree`, `search_repo`, `read_file`, `edit_file`, `run_test`, `git_diff`, and `rollback`.
- JSONL trajectory logger.
- Reward calculator v1 with test pass flags, patch size metrics, test modification flag, hardcode suspicion flag, regression flag, and total reward.
- Deterministic prompt-only baseline with `noop` and `gold` simulation modes.
- Evaluation runner and aggregate metrics.
- Forge-style baseline/demo runtime package under `codeguide_agent/runtime/`.
- Mini-Repo-Debug evaluator entry point at `codeguide_agent/eval_mini_repo.py`.
- Heuristic/localize-only rollout policy for non-gold process-localization baselines.
- Small LLM-backed rollout policy with mock and OpenAI-compatible backends.
- `eval_compare` policy comparison report.
- Aider baseline runner with skipped-if-unavailable behavior and canonical scoring.
- Skeleton SFT/DPO/GRPO data builder modules.
- Forge baseline runner entry point.

## Dataset Validation

Run:

```bash
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
```

Or:

```bash
bash scripts/validate_mini_repo_debug.sh
```

The validator checks each task for required files, metadata commands, gold files/functions, forbidden behaviors, and a valid repo path. It also warns if a task has zero public tests passing before any patch, because regression detection needs at least one public behavior that already works in the buggy state.

Run the static issue-text leakage audit:

```bash
python -m codeguide_agent.dataset.audit_leakage --root data/mini_repo_debug
```

The audit checks that `issue.md` does not reveal evaluator-only gold files,
gold functions, `metadata.json`, `gold.patch`, or `tests_hidden`.

## Evaluation

Run the canonical rollout/evaluation path:

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted
```

This path uses `RolloutCollector`, isolated temp workspaces, original-repo
checksum verification, `codeguide_agent/tools/*`, JSONL trajectory logging, and
the canonical reward formula in `codeguide_agent.reward.calculator`.

Localization reports distinguish process discovery from patch landing:

- `gold_file_hit_at_3` / `gold_function_hit_at_3`: the agent surfaced or opened the gold location during exploration.
- `gold_file_patched` / `gold_function_patched`: the final patch touched the gold location.

These can disagree. A blind gold-style patch can have `gold_file_patched=True`
while `gold_file_hit_at_3=False`.

Leakage means evaluator-oracle access, not successful localization. Accessing
`metadata.json`, `gold.patch`, `tests_hidden`, hidden-test payloads, or using a
gold path/function before it was surfaced by legal tools is leakage. A gold
file/function name appearing through `repo_tree`, `search_repo`, `read_file`, or
public logs is recorded as `gold_identifier_visible` for diagnostics and does
not by itself make `leakage_detected=True`.

For forge-runtime baseline comparison only, run:

```bash
python -m codeguide_agent.eval_mini_repo --tasks data/mini_repo_debug/tasks.jsonl
```

This command copies each task repo into `/tmp/codeguide_mini_repo_eval`,
initializes git, runs a deterministic forge-style baseline, executes public and
hidden tests with timeouts, computes comparable reward metrics with
`reward.calculator`, verifies the canonical dataset checksum, and writes:

- `data/mini_repo_debug/trajectories/<task_id>_forge.jsonl`
- `data/mini_repo_debug/reports/eval_report.json`

Run the older Phase 1 no-op baseline evaluation:

```bash
bash scripts/run_phase1_eval.sh
```

The evaluation scans `data/mini_repo_debug/tasks.jsonl` when present, otherwise scans `data/mini_repo_debug/repos/`. It executes public and hidden test commands, logs trajectories, calculates reward metrics, and prints a summary with pass rates, changed-file statistics, reward-hacking flags, and tool-call counts.

To run a gold-patch simulation for a single task:

```bash
python -m codeguide_agent.baselines.prompt_only data/mini_repo_debug/repos/task_001 --mode gold
```

## Rollout Collection

Collect local deterministic rollouts in isolated temp workspaces:

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy noop
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted --task-id task_001
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy heuristic
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy llm --limit 1
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy gold --run-hidden
```

Supported local policies are `noop`, `scripted`, `heuristic`, `localize_only`,
`llm`, and `gold`. Gold/scripted results validate the pipeline and should not
be presented as real LLM agent capability.

`heuristic` is the first real non-gold process-localization baseline. It ranks
source files from issue keywords, searches/reads likely files, and stops without
editing. Its success rate is expected to remain `0.0`; its purpose is to test
repo navigation and `gold_file_hit_at_k` / `gold_function_hit_at_k` metrics.

`llm` is the first patch-capable non-gold rollout policy. In local validation it
defaults to mock mode, so it does not require paid API access. Mock mode emits a
small safe action sequence (`repo_tree`, `search_repo`, `read_file`, `stop`) and
is meant to validate prompt boundaries, trajectories, reward, and comparison
plumbing, not repair strength.

To use a real OpenAI-compatible backend, configure:

```bash
export CODEGUIDE_LLM_BACKEND=openai_compatible
export CODEGUIDE_LLM_BASE_URL=https://your-compatible-endpoint/v1
export CODEGUIDE_LLM_API_KEY=...
export CODEGUIDE_LLM_MODEL=...
```

Optional guards include `CODEGUIDE_LLM_TIMEOUT`,
`CODEGUIDE_LLM_MAX_TOKENS`, `CODEGUIDE_LLM_TEMPERATURE`,
`CODEGUIDE_LLM_BUDGET_USD`, `CODEGUIDE_LLM_MAX_CALLS_PER_TASK`,
`CODEGUIDE_LLM_MAX_CONCURRENCY`, `CODEGUIDE_LLM_QPS_LIMIT`,
`CODEGUIDE_LLM_DRY_RUN`, and `CODEGUIDE_LLM_MOCK`.

The LLM prompt boundary excludes evaluator-only files and metadata:
`metadata.json`, `gold.patch`, `tests_hidden/`, hidden test commands/logs,
gold files/functions from task metadata, and gold patches. Hidden tests remain
evaluator-only. P3C is rollout/evaluation infrastructure only, not training.

Compare policies:

```bash
python -m codeguide_agent.eval_compare --root data/mini_repo_debug --policies noop,scripted,heuristic,gold,aider,llm --limit 5
```

The comparison report is written to `data/mini_repo_debug/reports/eval_compare.json`.
Rows for `gold` are pipeline validation only. The `aider` row is a strong
external baseline row, not CodeGuide-Agent's implementation base.

## Aider Baseline

Run the P3B Aider baseline with:

```bash
python -m codeguide_agent.baselines.aider_runner \
  --root data/mini_repo_debug \
  --limit 5 \
  --output data/mini_repo_debug/reports/aider_baseline_report.json
```

If the `aider` CLI or required model/API configuration is unavailable, the
runner writes a skipped report and exits `0` so local validation remains
reproducible without paid APIs. When available, it copies each task into an
isolated sanitized temp workspace, removes evaluator-only files before the
Aider run, restores hidden tests only after Aider exits, and scores the result
through `codeguide_agent.reward.calculator` plus the strict leakage checker.
No teacher-data export is performed in P3B.

Build SFT-style chat data from trajectory JSONL files:

```bash
python -m codeguide_agent.data_builders.build_sft \
  --input data/mini_repo_debug/trajectories \
  --output data/mini_repo_debug/sft/phase2_sft.jsonl
```

Gold-policy trajectories are excluded from SFT data even when they pass tests.
They are pipeline-validation artifacts only and may contain synthetic actions
such as `apply_gold_patch` that a real agent must not learn to imitate.

## Not Implemented Yet

- Model training.
- GRPO or rollout-group optimization.
- IDE completion.
- VLM or screenshot-based code understanding.
- Generic multi-agent orchestration.
- Paid or external API integrations.
- Real LLM patch generation in the migrated forge runtime.
- Aider teacher-data export.
- Strong LLM repair claims.

## Next Steps

- Expand Mini-Repo-Debug after P3 foundations are stable.
- Mine successful trajectories into SFT examples.
- Build DPO pairs from verified good/bad patch attempts.
- Add GRPO rollout grouping only after stochastic clean non-gold rollouts exist.\n\n<!-- P12_PROJECT_HIGHLIGHTS_START -->\n## Mini-Repo-Debug Pipeline Highlights\n\nCodeGuide-Agent includes a reproducible Mini-Repo-Debug pipeline for coding-agent training data construction.\n\nCore capabilities:\n\n- 20-task Mini-Repo-Debug benchmark for small-repo bug fixing.\n- Real rollout analysis with public-test and hidden-test diagnostics.\n- SFT candidate export from successful trajectories.\n- Preference pair mining from public-pass-hidden-fail trajectories.\n- Sanitization gates to avoid exposing hidden tests, metadata paths, gold patch paths, or raw test outputs.\n- Train-ready package generation with quality gate.\n- Dry-run trainer, replay eval, mock experiment artifact, and trained policy interface.\n- Clean-check validation showing unit tests do not depend on generated trajectories.\n\nUseful commands:\n\n- make test\n- make clean-check\n- make validate-pipeline\n- make clean-generated\n\nStable tag:\n\n- mini-repo-debug-p4-p11-stable\n\nSee also:\n\n- docs/PROJECT_STORY.md\n- docs/P11_REPRODUCIBLE_RUNBOOK.md\n<!-- P12_PROJECT_HIGHLIGHTS_END -->\n\n<!-- P14_INTERVIEW_DOCS_START -->
## Interview and Project Docs

- docs/INTERVIEW_PROJECT_BRIEF.md
- docs/PROJECT_STORY.md
- docs/RESUME_BULLETS.md
- docs/P11_REPRODUCIBLE_RUNBOOK.md
- docs/P13_CI_RELEASE_CHECK.md
<!-- P14_INTERVIEW_DOCS_END -->
