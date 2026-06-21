# P31 Data Expansion Plan

## Goal

Move CodeGuide-Agent from a 20-task pipeline demo toward a training-ready coding-agent data pipeline.

## Current scale

- Active Mini-Repo-Debug tasks: 20
- SFT records: 19
- Preference records: 23
- Hard preference records: 1

## Target before meaningful training

- Active tasks: 100+
- SFT records: 150+
- Preference records: 100+
- Hard preference records: 30+

## Expansion strategy

### Stage 1: Mini-Repo-Debug manual expansion

Add task_021-task_030 first.

Purpose:

- keep task quality controllable;
- produce more public-pass-hidden-fail cases;
- validate promotion / rollout / export / audit pipeline.

### Stage 2: SWE-Gym integration

Use SWE-Gym as the first external training-oriented benchmark source.

Purpose:

- add real-world repository tasks;
- use executable verification;
- align with software-engineering-agent training literature.

### Stage 3: SWE-smith generation

Use SWE-smith-style task generation after the internal pipeline is stable.

Purpose:

- scale task count beyond hand-written Mini-Repo-Debug;
- generate diverse repair/localization tasks;
- produce enough SFT and preference data.

### Stage 4: SWE-bench evaluation

Use SWE-bench Lite and SWE-bench Verified as held-out evaluation targets.

Rules:

- do not train on SWE-bench Verified;
- avoid mixing eval instances into training;
- use SWE-bench Lite for cheaper mid-stage eval;
- use SWE-bench Verified for final reporting.

## Immediate next action

Create 10 real tasks:

- task_021
- task_022
- task_023
- task_024
- task_025
- task_026
- task_027
- task_028
- task_029
- task_030

Each task must include:

- issue.md
- buggy source
- public tests
- hidden tests
- metadata
- gold.patch
- validator pass
- no model-facing leakage
