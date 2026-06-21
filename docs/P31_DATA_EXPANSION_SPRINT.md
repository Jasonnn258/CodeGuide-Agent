# P31 Data Expansion Sprint

## Goal

Move Mini-Repo-Debug from a 20-task pipeline demo toward a training-ready dataset.

Immediate target:

- Add task_021-task_030 as 10 real tasks.
- Each task must have real buggy code, public tests, hidden tests, metadata, and gold.patch.
- Each task should create a public-hidden generalization gap.
- The goal is to increase SFT/preference candidates, especially hard public-pass-hidden-fail cases.

## Current scale

- Active tasks: 20
- SFT records: 19
- Preference records: 23
- Hard preference records: 1

## Training threshold

Do not claim meaningful training until at least:

- Active tasks >= 100
- SFT records >= 150
- Preference records >= 100
- Hard preference records >= 30

## External benchmark strategy

Use external benchmarks carefully:

- Mini-Repo-Debug remains the controllable training-data sandbox.
- SWE-Gym / SWE-smith-style tasks can be integrated later for scale.
- SWE-bench Lite / Verified should be held out for evaluation, not mixed into training.
- Do not train on the same instances used for final evaluation.

## P31 task plan

| Task | Bug type | Public test covers | Hidden test covers | Expected hard-pair potential |
| --- | --- | --- | --- | --- |
| task_021 | string_normalization | lowercase / simple whitespace | mixed case, repeated spaces, punctuation | medium |
| task_022 | path_handling | simple relative path | nested path, parent dir, absolute-like input | high |
| task_023 | cache_key | one argument cache | parameter-sensitive cache key collision | high |
| task_024 | optional_default_args | omitted optional arg | explicit mutable arg should not be mutated | high |
| task_025 | boundary_condition | normal non-empty list | empty list, single item, last item | medium |
| task_026 | json_config_parsing | valid JSON config | missing optional fields, bad types, blank config | medium |
| task_027 | cli_argument_propagation | direct function call | CLI flag propagation to helper | high |
| task_028 | sorting_filtering | simple sort/filter | duplicates, stable tie-breaking, None values | medium |
| task_029 | error_handling | happy path | missing resource should raise specific error | medium |
| task_030 | multi_file_integration | helper function behavior | service wrapper uses helper correctly | high |

## Acceptance checklist for each task

Each task must satisfy:

- public tests fail on buggy code or expose incomplete behavior;
- hidden tests fail on buggy code;
- gold.patch passes public tests;
- gold.patch passes hidden tests;
- public tests can be passed by a narrow patch;
- hidden tests catch at least one narrow patch;
- issue.md does not mention tests_hidden, metadata.json, gold.patch, or exact hidden cases;
- metadata.json is complete;
- no model-facing leakage;
- validator passes;
- clean-check, audit, docs-check, canonical-check still pass.

## Execution order

1. Create task_021-task_030 design skeletons.
2. Implement task_021-task_025 first.
3. Run validator and tests.
4. Generate rollout trajectories.
5. Export SFT/preference candidates.
6. Inspect whether hard preference count increases.
7. Implement task_026-task_030.
8. Repeat rollout/export/scale report.
