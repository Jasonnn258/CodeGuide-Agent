# CodeGuide-Agent

CodeGuide-Agent is a verifier-driven code repair agentic RL system focused on Auto Repair / repo-level debugging.

Phase 1 builds the local deterministic infrastructure for Mini-Repo-Debug: dataset schema, handcrafted mini repos, shared tools, trajectory logging, reward calculation, a simple baseline runner, and evaluation scripts.

Phase 2A adds a deterministic rollout collector skeleton and an SFT data builder. It still does not implement training, GRPO, IDE completion, VLM, or generic multi-agent workflows.

## Project Positioning

The main scenario is:

```text
Issue + Mini Repo + Failing Tests
→ repo navigation
→ fault localization
→ minimal patch
→ public/hidden test verification
→ trajectory log
→ verifier reward
```

This repository intentionally does not expand Phase 1 into IDE completion, VLM workflows, generic multi-agent systems, model training, or large-scale GRPO.

## Phase 1 Scope

Implemented components:

- Mini-Repo-Debug task schema and validator.
- Five handcrafted Python pytest mini repos under `data/mini_repo_debug/repos/`.
- Shared tool layer: `repo_tree`, `search_repo`, `read_file`, `edit_file`, `run_test`, `git_diff`, and `rollback`.
- JSONL trajectory logger.
- Reward calculator v1 with test pass flags, patch size metrics, test modification flag, hardcode suspicion flag, regression flag, and total reward.
- Deterministic prompt-only baseline with `noop` and `gold` simulation modes.
- Evaluation runner and aggregate metrics.

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

Run the Phase 1 no-op baseline evaluation:

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

## Not Implemented Yet

- Model training.
- GRPO or rollout-group optimization.
- IDE completion.
- VLM or screenshot-based code understanding.
- Generic multi-agent orchestration.
- Paid or external API integrations.
