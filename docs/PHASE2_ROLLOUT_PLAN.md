# Phase 2 Rollout Plan

## What The Rollout Collector Does

The Phase 2A rollout collector creates an isolated temporary copy of each Mini-Repo-Debug task, initializes rollout state, asks a deterministic local policy for structured actions, validates those actions, executes existing tools, logs action-observation steps, computes reward, and verifies the original task repo checksum is unchanged.

P1 hardening adds process localization metrics, regression-detectable public
test accounting, and static leakage checks. This is still infrastructure
hardening, not evidence of real LLM repair capability.

Supported policy backends:

- `noop`: emits `stop`.
- `scripted`: runs a deterministic repo-tree, search, and read flow.
- `heuristic` / `localize_only`: ranks source files from issue keywords,
  searches/reads likely files, and stops without editing.
- `gold`: applies `gold.patch` only inside the temp workspace, then runs verifiers.
- `aider`: external Aider baseline run through `codeguide_agent.baselines.aider_runner`
  and canonical scoring. It is skipped if the CLI or API/model config is
  unavailable.
- `llm`: small non-gold LLM-backed policy. It defaults to mock mode for local
  validation and can call an OpenAI-compatible endpoint when explicitly
  configured.

## What It Does Not Do Yet

- It does not train a model.
- It does not implement GRPO.
- It does not require paid APIs for local validation; Aider is optional and
  skips cleanly when unavailable, and LLM rollout defaults to mock mode.
- It does not add IDE completion, VLM, or generic multi-agent workflows.
- It does not expand beyond Mini-Repo-Debug.
- It does not modify canonical dataset repos.

## How To Run Rollout

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy noop
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted --task-id task_001
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy heuristic
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy llm --limit 1
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy gold --run-hidden
```

Useful flags:

- `--task-id task_001` to run one task.
- `--max-steps 8` to cap action loops.
- `--temp-root /tmp/codeguide_eval` to choose isolated workspaces.
- `--keep-temp` to inspect temp repos after rollout.
- `--output data/mini_repo_debug/rollouts/phase2_rollouts.jsonl` to save rollout summaries.

## P1 Metrics And Audits

Localization metrics are split into two families:

- `gold_file_hit_at_3`, `gold_file_hit_at_5`, `gold_function_hit_at_3`, and
  `gold_function_hit_at_5` measure whether exploration surfaced or opened the
  gold location before patching.
- `gold_file_patched` and `gold_function_patched` measure whether the final
  diff landed on the gold location.

Leakage metrics are split from localization metrics:

- `forbidden_file_access` flags evaluator-only paths such as `metadata.json`,
  `gold.patch`, and `tests_hidden`.
- `oracle_metadata_leakage` flags actions that appear to use evaluator metadata
  before the information was legally surfaced.
- `gold_identifier_visible` is diagnostic only. Gold file/function strings that
  appear through legal repo exploration are expected and should be measured by
  localization metrics, not punished as leakage.
- `leakage_detected` is strict: `forbidden_file_access or oracle_metadata_leakage`.

Each public test suite should contain at least one test that passes before the
bug fix. The validator warns when this is not true because regression detection
depends on comparing pre-patch and post-patch public pass counts.

Run the static issue leakage audit with:

```bash
python -m codeguide_agent.dataset.audit_leakage --root data/mini_repo_debug
```

Compare policies with:

```bash
python -m codeguide_agent.eval_compare --root data/mini_repo_debug --policies noop,scripted,heuristic,gold,aider,llm --limit 5
```

The heuristic policy is the first non-gold process-localization baseline. It is
not expected to pass tests because it does not patch. It exists to validate repo
navigation and process localization metrics before LLM or Aider policies.

Run the Aider baseline directly with:

```bash
python -m codeguide_agent.baselines.aider_runner \
  --root data/mini_repo_debug \
  --limit 5 \
  --output data/mini_repo_debug/reports/aider_baseline_report.json
```

P3B uses Aider as a baseline only. The runner builds prompts from `issue.md`
and the public test command, runs in a sanitized temp workspace without
`metadata.json`, `gold.patch`, or `tests_hidden/`, restores hidden tests only
after Aider exits, and scores through `codeguide_agent.reward.calculator` plus
strict leakage checks. It does not export Aider teacher data.

P3C adds a small LLM-backed policy for real non-gold action trajectories:

```text
issue -> repo_tree/search/read/edit/test -> trajectory -> reward -> eval_compare
```

Environment variables:

```text
CODEGUIDE_LLM_BACKEND
CODEGUIDE_LLM_MODEL
CODEGUIDE_LLM_BASE_URL
CODEGUIDE_LLM_API_KEY
CODEGUIDE_LLM_TIMEOUT
CODEGUIDE_LLM_MAX_TOKENS
CODEGUIDE_LLM_TEMPERATURE
CODEGUIDE_LLM_BUDGET_USD
CODEGUIDE_LLM_MAX_CALLS_PER_TASK
CODEGUIDE_LLM_MAX_CONCURRENCY
CODEGUIDE_LLM_QPS_LIMIT
CODEGUIDE_LLM_DRY_RUN
CODEGUIDE_LLM_MOCK
```

With no real backend configured, the policy runs in deterministic mock mode so
tests and local validation require no paid API access. The prompt must include
only allowed context: issue text, public test command/output, repo tree/search
results, read-file output from allowed files, and recent observation summaries.
It must not include evaluator-only metadata, hidden test commands/logs,
`metadata.json`, `gold.patch`, `tests_hidden/`, gold files/functions from
metadata, or gold patches. P3C is rollout/eval infrastructure only; it is not a
training phase and should not be used to claim strong repair ability yet.

## How To Build SFT Data

```bash
python -m codeguide_agent.dataset.export_training_candidates \
  --root data/mini_repo_debug \
  --out data/mini_repo_debug/exports
```

The builder reads trajectory JSONL files, keeps successful non-gold
trajectories, and writes chat-format samples with:

- system message;
- user task instruction;
- action turns;
- observation turns;
- final patch or stop information;
- metadata outside the model-visible messages.

Hidden test commands and hidden test logs are excluded from model-visible messages.
Gold-policy trajectories are excluded entirely. They are pipeline-validation
artifacts only and may contain synthetic actions such as `apply_gold_patch`;
they must not enter SFT or DPO data.

## Path To Future SFT / Distillation / GRPO

Phase 2A produces the raw interface needed for later learning:

- rollout trajectories for behavior traces;
- invalid-action statistics for process penalties;
- opened-file and suspicious-file evidence for grounding;
- SFT JSONL for supervised tool-use formatting;
- verifier reward outputs for future rollout ranking.

Future phases can add SFT and distillation once the local rollout/eval path is stable. GRPO should remain deferred until stochastic clean non-gold rollouts exist and there is enough reward-hacking analysis.
