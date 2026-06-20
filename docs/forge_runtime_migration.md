# Forge Runtime Migration

## Purpose

CodeGuide-Agent includes a forge-style runtime adapted from an earlier local
prototype available as `/Users/yjx/Code/forge-agent`. The local checkout has a
GitHub remote (`https://github.com/muk610648-design/forge-agent.git`) but no
local license file was found, so the project uses conservative provenance
wording and does not present forge-agent as an open-source dependency.

This migration does not make CodeGuide-Agent a forked coding assistant. The
runtime is only the execution substrate. The main project remains a Code
Intelligence and Coding Agent research platform for:

- repo-level debugging agents,
- Mini-Repo-Debug tasks,
- fault localization evaluation,
- patch minimality and safety checks,
- process and outcome reward,
- trajectory mining,
- SFT/DPO/GRPO data builders,
- Aider baseline and teacher comparisons.

## What Was Adapted

The migration adds a compact forge-style baseline/demo runtime under
`codeguide_agent/runtime/`:

- `agent/types.py`: task/action/observation/event/run dataclasses.
- `agent/event_log.py`: JSONL trajectory writer.
- `agent/loop.py`: deterministic forge-style loop for local evaluation.
- `tools/`: file, search, shell, test, and git-diff tools with bounded command execution.
- `context/repo_map.py`: lightweight repository file map.
- `llm/`: backend boundary and mock fallback router.
- `entry/cli.py`: small manual runtime entry point.

The runtime currently uses a deterministic mock repair path for Mini-Repo-Debug
when no LLM key is configured. It applies each task's local `gold.patch` inside
an isolated temporary workspace. This is intentional for a robust first demo;
future versions can replace this policy with actual model calls and patch
generation while keeping the same event-log and evaluation interfaces.

The canonical rollout/evaluation path is separate: `RolloutCollector` uses
`codeguide_agent/tools/*` and `reward.calculator`. That path is the current
main research execution path; `codeguide_agent/runtime/` is not the single
engineering base for all evaluation.

## Safety Choices

- Evaluation copies each task repo into `/tmp/codeguide_mini_repo_eval`.
- The original dataset repos are not edited by `eval_mini_repo`.
- Test and shell commands use subprocess timeouts.
- Shell tooling blocks obvious destructive command patterns.
- The first version does not run network APIs or install dependencies.

## Current Gaps

- The LLM router exposes only a mock backend.
- The runtime does not yet implement Aider-style edit formats.
- DPO/GRPO builders are CLI skeletons only.
- The Aider runner is a documented TODO, not a full integration.

## Next Steps

1. Add a real model backend behind `codeguide_agent.runtime.llm.router`.
2. Replace gold-patch mock repair with model-produced candidate patches.
3. Mine event logs into SFT examples.
4. Add DPO pair construction from successful and failed patch attempts.
5. Add GRPO rollout grouping once multiple stochastic repair attempts exist.
