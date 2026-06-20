# AGENTS.md

## Project Identity

CodeGuide-Agent is a research-oriented Code Intelligence and Coding Agent platform.

It is **not** a thin wrapper around an existing coding assistant. The core contribution is the research stack around coding agents:

* Mini-Repo-Debug datasets;
* repo-level fault localization evaluation;
* patch minimality and safety verification;
* process-level and outcome-level reward;
* trajectory mining;
* SFT / DPO / GRPO data-builder skeletons;
* baseline comparison against forge-style runtime, Aider, and future LLM policies.

The current first target is verifier-driven repo-level debugging on Mini-Repo-Debug tasks.

---

## Current Project Stage

The project is currently in **P2 cleanup before Phase 2 expansion**.

Phase 1 has already implemented:

* forge-style runtime under `codeguide_agent/runtime/`;
* Mini-Repo-Debug task schema and evaluator;
* five handcrafted Python mini repo tasks;
* shared tools: `repo_tree`, `search_repo`, `read_file`, `edit_file`, `run_test`, `git_diff`, `rollback`;
* JSONL trajectory logging;
* reward calculator v1;
* deterministic `noop`, `scripted`, and `gold` rollout policies;
* evaluation runner and aggregate metrics;
* SFT/DPO/GRPO data-builder skeletons;
* docs for forge runtime migration and Aider positioning.

Completed hardening:

* Phase 1.5 / P0 hardening is complete.
* P1 infrastructure hardening is complete.

Current next priorities:

* P2 cleanup: provenance/positioning and data-builder consolidation.
* P3 non-gold policy plus Aider baseline.
* Then expand Mini-Repo-Debug beyond the current 5 tasks.

---

## Important Design Principle

Do **not** optimize for a generic coding assistant UX first.

Optimize for:

```text
Issue + Repo + Tests
→ repo navigation
→ fault localization
→ minimal patch
→ public/hidden test verification
→ trajectory log
→ verifier reward
→ training data
```

The project should make it easy to answer:

1. Did the agent find the right file?
2. Did the agent find the right function?
3. Did the agent open too many irrelevant files?
4. Did the agent patch before localizing the root cause?
5. Was the patch minimal?
6. Did the patch delete tests or hard-code expected outputs?
7. Did public tests pass?
8. Did hidden tests pass?
9. Did previously passing tests regress?
10. Can this trajectory become SFT / DPO / GRPO data?

---

## Repository Layout

Expected high-level layout:

```text
CodeGuide-Agent/
  README.md
  AGENTS.md
  NOTICE.md
  pyproject.toml

  docs/
    design_v0.6.md
    design_v0.7.md
    forge_runtime_migration.md
    aider_baseline_teacher_reference.md

  codeguide_agent/
    runtime/
      agent/
      tools/
      context/
      llm/
      entry/

    datasets/
      mini_repo_debug.py

    evaluators/
      localization_eval.py
      patch_eval.py

    reward/
      outcome_reward.py
      process_reward.py

    data_builders/
      build_sft.py
      build_dpo.py
      build_grpo_rollouts.py

    baselines/
      aider_runner.py
      forge_runner.py

    testing/
      simple_pytest.py

    eval_mini_repo.py

  data/
    mini_repo_debug/
      tasks.jsonl
      repos/
      trajectories/
      reports/

  scripts/
    run_phase1_eval.sh
    validate_mini_repo_debug.sh
```

Keep runtime code and CodeGuide research code conceptually separate:

```text
runtime/             = how the agent runs
datasets/            = what tasks it runs
evaluators/          = how we measure behavior
reward/              = how signals become reward
data_builders/       = how trajectories become training data
baselines/           = how we compare against other systems
```

---

## Runtime Base Policy

The project includes a compact forge-style runtime package, but the canonical
Mini-Repo-Debug rollout path currently uses `RolloutCollector` and
`codeguide_agent/tools/*`.

The runtime package is adapted from an earlier local prototype at
`/Users/yjx/Code/forge-agent`. The inspected local checkout has a GitHub remote
but no local license file, so do not describe it as an open-source dependency
or as the sole engineering base.

The runtime package provides a baseline/demo implementation of:

* agent loop boundary;
* task/action/observation dataclasses;
* JSONL event logging;
* tool registry;
* file/search/shell/test/git tools;
* repo map/context;
* LLM backend routing;
* CLI entry points.

See:

```text
NOTICE.md
docs/forge_runtime_migration.md
```

---

## Aider Policy

Aider is **not** the main base of CodeGuide-Agent.

Aider should be used as:

1. **Strong baseline**
   Compare CodeGuide-Agent against a mature AI pair-programming tool.

2. **Teacher / data generator**
   Use Aider-generated successful patches only after verifier filtering.

3. **Repo-map / edit-format reference**
   Borrow design ideas such as repo-map, symbol-aware context, and stable diff/edit format.

Do not position the project as “Aider wrapper”.

See:

```text
docs/aider_baseline_teacher_reference.md
```

---

## No-Leakage Rules

For real agent policies and baselines, the agent must not read:

```text
metadata.json
gold.patch
tests_hidden/
```

These files are evaluator-only.

Allowed to agent:

```text
issue.md
README.md
src/
tests/
public test commands
repo tree
public traceback/logs
```

Evaluator should track:

```text
leakage_detected
forbidden_file_access
invalid_trajectory
```

If leakage is detected, mark the trajectory invalid and apply reward penalty.

---

## Mini-Repo-Debug Task Requirements

Each Mini-Repo-Debug task should include:

```text
issue.md
README.md
src/
tests/
tests_hidden/
metadata.json
gold.patch
```

Each task must satisfy:

1. buggy version fails at least one public or hidden test;
2. gold patch passes public and hidden tests;
3. issue does not directly reveal gold file/function/exact fix;
4. gold file and gold function are listed in `metadata.json`;
5. public and hidden test commands are valid;
6. task is small enough for fast local evaluation;
7. hidden tests are only used by evaluator.

Preferred bug categories:

* parser/config bug;
* CLI argument bug;
* path/file I/O bug;
* cache/state bug;
* data processing bug;
* API compatibility bug;
* error handling bug;
* cross-file call-chain bug;
* simple security bug.

---

## Evaluation Metrics

Core metrics:

```text
gold_file_hit_at_3
gold_file_hit_at_5
gold_function_hit_at_3
gold_function_hit_at_5
gold_file_patched
gold_function_patched
public_test_pass
hidden_test_pass
pre_public_pass_count
pre_public_fail_count
post_public_pass_count
post_public_fail_count
patch_size
no_test_deletion
no_hardcode
regression
leakage_detected
process_reward_total
outcome_reward_total
```

Useful aggregate metrics:

```text
task_success_rate
public_test_pass_rate
hidden_test_pass_rate
gold_file_hit_at_3_rate
gold_function_hit_at_3_rate
gold_file_patched_rate
gold_function_patched_rate
average_patch_size
no_test_deletion_rate
no_hardcode_rate
regression_rate
average_process_reward_total
average_total_reward
```

Remember:

Perfect results from `gold` or scripted policies are pipeline validation, not real agent performance.

Do not claim true agent capability from gold-patch simulations.

---

## Required Local Commands

Validate dataset:

```bash
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
```

Run leakage audit:

```bash
python -m codeguide_agent.dataset.audit_leakage --root data/mini_repo_debug
```

Run Mini-Repo-Debug evaluation:

```bash
python -m codeguide_agent.eval_mini_repo --tasks data/mini_repo_debug/tasks.jsonl
```

Run deterministic rollouts:

```bash
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy noop
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy scripted --task-id task_001
python -m codeguide_agent.rollout.run_rollout --root data/mini_repo_debug --policy gold --run-hidden
```

Build SFT-style data from trajectories:

```bash
python -m codeguide_agent.data_builders.build_sft \
  --input data/mini_repo_debug/trajectories \
  --output data/mini_repo_debug/sft/phase2_sft.jsonl
```

---

## Coding Guidelines

Use small, explicit modules.

Prefer:

* dataclasses or typed dicts for task/action/observation records;
* JSONL for trajectories;
* JSON for reports;
* deterministic tests;
* timeouts for shell commands;
* isolated temporary workspaces;
* no hidden-test leakage;
* clear CLI entry points.

Avoid:

* large implicit global state;
* destructive shell commands;
* unbounded command execution;
* reading evaluator-only files inside agent policies;
* claiming training results before training exists;
* hiding gold/scripted behavior as real agent ability.

---

## Baseline Policy

The project should maintain multiple baselines:

```text
noop
scripted
gold
heuristic / localize_only
forge runtime baseline
Aider baseline
future LLM policy
```

The `gold` baseline is only for pipeline validation.

Real comparisons should separate:

```text
gold/scripted pipeline validation
vs
non-gold policy performance
vs
Aider baseline performance
vs
future LLM policy performance
```

---

## Data Builder Policy

Data builders should be conservative.

SFT data should only include:

* successful trajectories;
* verifier-passed trajectories;
* no leakage;
* no hard-code;
* no test deletion.

DPO pairs should use:

```text
chosen:
  successful, minimal, no leakage, no regression

rejected:
  failed, leakage, hard-code, test deletion, high-cost, regression
```

GRPO rollout grouping should remain a skeleton until stochastic LLM policy sampling exists.

---

## Documentation Policy

Keep README focused on:

* project positioning;
* current implemented scope;
* how to validate data;
* how to run evaluation;
* rollout collection;
* what is not implemented yet;
* next steps.

Keep docs focused on design decisions:

```text
docs/design_v0.6.md
docs/design_v0.7.md
docs/forge_runtime_migration.md
docs/aider_baseline_teacher_reference.md
```

When adding major functionality, update README and docs together.

---

## Current Next Priorities

1. Finish P2 cleanup: conservative runtime provenance and canonical data-builder paths.
2. Implement P3 non-gold heuristic/localize-only policy.
3. Implement Aider baseline runner.
4. Add `eval_compare` for baseline comparison.
5. Expand Mini-Repo-Debug to 20+ tasks after P2/P3 foundations are stable.
6. Add DPO pair builder with chosen/rejected filtering.
7. Generate a Phase 2 baseline evaluation report.

---

## Project Story for Reviewers

CodeGuide-Agent started from CodeGuide-LLM, a response-level algorithm teaching model. The project evolved because real Coding Agent capability is not just “write code from scratch”. The harder and more valuable problem is:

```text
Given an issue and a repo,
can the agent navigate the codebase,
localize the root cause,
produce a minimal patch,
verify with tests,
avoid reward hacking,
and turn the trajectory into training data?
```

Therefore, CodeGuide-Agent focuses on the research infrastructure around coding agents:

```text
dataset → runtime → evaluation → reward → trajectory → SFT/DPO/GRPO data
```

This is the main contribution.
