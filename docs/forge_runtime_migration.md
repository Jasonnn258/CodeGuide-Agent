# Forge Runtime Migration

## Purpose

CodeGuide-Agent uses `/Users/yjx/Code/forge-agent` as the engineering
base/runtime because its architecture is close to the research loop this
project needs: task input, ReAct-style agent loop, tool registry, repository
context, bounded shell/test tools, and append-only JSONL events.

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

The first migration adds a compact forge-style runtime under
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

## Safety Choices

- Evaluation copies each task repo into `/tmp/codeguide_mini_repo_eval`.
- The original dataset repos are not edited by `eval_mini_repo`.
- Test and shell commands use subprocess timeouts.
- Shell tooling blocks obvious destructive command patterns.
- The first version does not run network APIs or install dependencies.

## Current Gaps

- The LLM router exposes only a mock backend.
- The runtime does not yet implement Aider-style edit formats.
- Data builders for SFT/DPO/GRPO are CLI skeletons only.
- The Aider runner is a documented TODO, not a full integration.

## Next Steps

1. Add a real model backend behind `codeguide_agent.runtime.llm.router`.
2. Replace gold-patch mock repair with model-produced candidate patches.
3. Mine event logs into SFT examples.
4. Add DPO pair construction from successful and failed patch attempts.
5. Add GRPO rollout grouping once multiple stochastic repair attempts exist.
