# P19 Planned Task Promotion Gate

P19 defines the gate for promoting a planned task skeleton into the active Mini-Repo-Debug benchmark.

## Commands

Generate a report for all planned skeletons:

make promotion-report

Check one planned task:

make promotion-check TASK=task_021

## Why this exists

P18 skeletons are planning artifacts. They must not be counted as active benchmark tasks and must not be used for training export.

A task can only be promoted after it has real source code, real public tests, real hidden tests, real metadata, and a real gold patch.

## Promotion readiness conditions

A planned task is blocked if:

- required files are missing;
- issue.md still contains TODO;
- public or hidden tests are placeholders;
- source code is still placeholder code;
- gold.patch is not a real unified git diff;
- metadata status is still planned_skeleton;
- target_files is empty;
- expected_failure_mode is not defined;
- generalization_axis is not defined;
- issue.md leaks tests_hidden, metadata.json, gold.patch, or apply_gold_patch.

## Promotion workflow

1. Generate planned skeletons with make task-skeletons.
2. Pick one task, for example task_021.
3. Replace placeholder source code with a real buggy implementation.
4. Replace public tests with meaningful public tests.
5. Replace hidden tests with generalization tests.
6. Write a real gold.patch.
7. Update metadata.json.
8. Run make promotion-check TASK=task_021.
9. Only after the check passes, copy the task into the active benchmark structure.
10. Run full validation, leakage audit, export, package, and clean-check.

## Current expectation

Right after skeleton generation, all planned tasks should be blocked. This is expected. The checker is not meant to mark placeholders as ready; it is meant to prevent accidental promotion.
