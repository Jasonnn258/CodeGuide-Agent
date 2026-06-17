# CodeGuide-Agent Design v0.9

CodeGuide-Agent remains focused on verifier-driven Auto Repair / repo-level debugging. The only mainline scenario is Mini-Repo-Debug: issue text plus a small repository, public/hidden tests, local tools, trajectory logging, and verifier reward.

## Current Scope

- Phase 1: dataset format, handcrafted tasks, shared tools, trajectory logger, reward v1, baseline runner, evaluation.
- Phase 1.5: isolated non-mutating evaluation, original repo checksum safety, explicit pytest dependency handling, reward-hacking checks, citation verifier skeleton.
- Phase 2A: deterministic rollout collector skeleton and SFT data builder.

## Explicit Non-Goals

- No model training yet.
- No GRPO yet.
- No IDE completion.
- No VLM workflows.
- No generic multi-agent orchestration.
- No SWE-bench, BugsInPy, or Defects4J expansion yet.

## Phase 2A Interface

The rollout collector consumes structured actions, executes existing tools in isolated temp task copies, logs action-observation steps, records invalid action counts, computes verifier reward, and checks original repo checksums. Policies are local and deterministic first: no-op, scripted search/read, and gold-patch simulation.

The SFT builder converts successful or gold trajectories into chat-format JSONL samples for future SFT/distillation work. It does not expose hidden test contents or evaluator-only metadata in model-visible messages.
