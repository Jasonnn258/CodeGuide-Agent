# Phase 2 Rollout Plan

## What The Rollout Collector Does

The Phase 2A rollout collector creates an isolated temporary copy of each Mini-Repo-Debug task, initializes rollout state, asks a deterministic local policy for structured actions, validates those actions, executes existing tools, logs action-observation steps, computes reward, and verifies the original task repo checksum is unchanged.

Supported policy backends:

- `noop`: emits `stop`.
- `scripted`: runs a deterministic repo-tree, search, and read flow.
- `gold`: applies `gold.patch` only inside the temp workspace, then runs verifiers.

## What It Does Not Do Yet

- It does not train a model.
- It does not implement GRPO.
- It does not call paid APIs.
- It does not add IDE completion, VLM, or generic multi-agent workflows.
- It does not expand beyond Mini-Repo-Debug.
- It does not modify canonical dataset repos.

## How To Run Rollout

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy noop
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted --task-id task_001
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy gold --run-hidden
```

Useful flags:

- `--task-id task_001` to run one task.
- `--max-steps 8` to cap action loops.
- `--temp-root /tmp/codeguide_eval` to choose isolated workspaces.
- `--keep-temp` to inspect temp repos after rollout.
- `--output data/mini_repo_debug/rollouts/phase2_rollouts.jsonl` to save rollout summaries.

## How To Build SFT Data

```bash
python -m codeguide_agent.training_data.build_sft_from_trajectories \
  --input data/mini_repo_debug/trajectories \
  --output data/mini_repo_debug/sft/phase2_sft.jsonl
```

The builder reads trajectory JSONL files, keeps successful or gold trajectories, and writes chat-format samples with:

- system message;
- user task instruction;
- action turns;
- observation turns;
- final patch or stop information;
- metadata outside the model-visible messages.

Hidden test commands and hidden test logs are excluded from model-visible messages.

## Path To Future SFT / Distillation / GRPO

Phase 2A produces the raw interface needed for later learning:

- rollout trajectories for behavior traces;
- invalid-action statistics for process penalties;
- opened-file and suspicious-file evidence for grounding;
- SFT JSONL for supervised tool-use formatting;
- verifier reward outputs for future rollout ranking.

Future phases can add SFT and distillation once the local rollout/eval path is stable. GRPO should remain deferred until there is enough clean trajectory data and reward-hacking analysis.
