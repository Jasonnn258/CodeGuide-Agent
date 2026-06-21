# P20-P22 Expansion Execution Pack

This pack turns the P16/P17 scaling plan into executable gates.

P20 adds planned task promotion.

Command:

make promote-task TASK=task_021

The command first runs promotion readiness checks. It only copies a planned task into the active benchmark if the planned task is ready.

P21 adds rollout batch planning.

Command:

make rollout-plan

This generates docs/ROLLOUT_BATCH_PLAN.json. It is an offline plan and does not call paid APIs.

P22 adds training readiness gating.

Command:

make readiness

This checks whether the project is ready for real training. Current expectation is NOT_READY because the active dataset and hard preference count are still too small.

Readiness requires:

- at least 100 active tasks;
- at least 150 SFT records;
- at least 100 preference records;
- at least 30 hard public-pass-hidden-fail preference records;
- clean-check passes;
- leakage audit passes.

This prevents overstating the project. The current project is pipeline-ready, not real-training-ready.
