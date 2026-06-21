# P18 Planned Task Skeleton Generator

P18 adds a generator for planned Mini-Repo-Debug task skeletons.

Command:

make task-skeletons

The generated skeletons are written to:

data/mini_repo_debug/planned_task_skeletons/

These skeletons are planning artifacts only. They are intentionally ignored by git and must not be counted as active benchmark tasks until each task has real source code, real public tests, real hidden tests, real metadata, and a real gold patch.

Why skeletons are kept outside the active dataset:

- They should not break existing validators.
- They should not inflate task_count claims.
- They should not be used for training data export.
- They provide a structured template for future expansion from 20 to 100 tasks.

Promotion rule:

A planned skeleton can only be promoted into the active Mini-Repo-Debug dataset after:

- public tests fail on buggy code;
- hidden tests fail on buggy code;
- gold patch passes public tests;
- gold patch passes hidden tests;
- leakage audit stays clean;
- task validator passes;
- the task has a meaningful public-hidden generalization gap.
