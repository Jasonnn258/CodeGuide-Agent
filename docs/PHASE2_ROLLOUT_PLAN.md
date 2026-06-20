# Phase 2 Rollout Plan

## What The Rollout Collector Does

The Phase 2A rollout collector creates an isolated temporary copy of each Mini-Repo-Debug task, initializes rollout state, asks a deterministic local policy for structured actions, validates those actions, executes existing tools, logs action-observation steps, computes reward, and verifies the original task repo checksum is unchanged.

P1 hardening adds process localization metrics, regression-detectable public
test accounting, and static leakage checks. This is still infrastructure
hardening, not evidence of real LLM repair capability.

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

## P1 Metrics And Audits

Localization metrics are split into two families:

- `gold_file_hit_at_3`, `gold_file_hit_at_5`, `gold_function_hit_at_3`, and
  `gold_function_hit_at_5` measure whether exploration surfaced or opened the
  gold location before patching.
- `gold_file_patched` and `gold_function_patched` measure whether the final
  diff landed on the gold location.

Each public test suite should contain at least one test that passes before the
bug fix. The validator warns when this is not true because regression detection
depends on comparing pre-patch and post-patch public pass counts.

Run the static issue leakage audit with:

```bash
python -m codeguide_agent.dataset.audit_leakage --root data/mini_repo_debug
```

## How To Build SFT Data

```bash
python -m codeguide_agent.data_builders.build_sft \
  --input data/mini_repo_debug/trajectories \
  --output data/mini_repo_debug/sft/phase2_sft.jsonl
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

Future phases can add SFT and distillation once the local rollout/eval path is stable. GRPO should remain deferred until there is enough clean trajectory data and reward-hacking analysis.
