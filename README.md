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

## Runtime Base

CodeGuide-Agent now includes a compact forge-agent-style runtime under
`codeguide_agent/runtime/`. It is adapted from the local
`/Users/yjx/Code/forge-agent` runtime for research use:

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
- Forge-style runtime package under `codeguide_agent/runtime/`.
- Mini-Repo-Debug evaluator entry point at `codeguide_agent/eval_mini_repo.py`.
- Skeleton SFT/DPO/GRPO data builder modules.
- Aider and forge baseline runner entry points.

## Dataset Validation

Run:

```bash
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
```

Or:

```bash
bash scripts/validate_mini_repo_debug.sh
```

The validator checks each task for required files, metadata commands, gold files/functions, forbidden behaviors, and a valid repo path.

## Evaluation

Run the canonical rollout/evaluation path:

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted
```

This path uses `RolloutCollector`, isolated temp workspaces, original-repo
checksum verification, `codeguide_agent/tools/*`, JSONL trajectory logging, and
the canonical reward formula in `codeguide_agent.reward.calculator`.

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
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy gold --run-hidden
```

Supported Phase 2A policies are `noop`, `scripted`, and `gold`. They are local and deterministic; no paid APIs are required.

Build SFT-style chat data from trajectory JSONL files:

```bash
python -m codeguide_agent.training_data.build_sft_from_trajectories \
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
- Full Aider automation.
- Real LLM patch generation in the migrated forge runtime.

## Next Steps

- Replace deterministic gold-patch mock repair with a real LLM backend.
- Add Aider baseline execution and verifier-filtered teacher data export.
- Mine successful trajectories into SFT examples.
- Build DPO pairs from verified good/bad patch attempts.
- Add GRPO rollout grouping after stochastic policy sampling exists.
