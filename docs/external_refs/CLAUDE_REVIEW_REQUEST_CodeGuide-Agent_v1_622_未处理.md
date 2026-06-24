# Claude Review Request — CodeGuide-Agent Mini-Repo-Debug v1

## 0. 审查目标

请将本项目作为一个 **coding-agent 数据集与训练流水线原型** 来 review，而不是作为一个已经完成训练的最终模型来 review。

当前里程碑：

* **Mini-Repo-Debug 数据集已完成 100 个 active tasks**
* **planned backlog 已清空**
* **SFT / preference / hard-preference 训练数据已导出**
* **尚未进行真实训练**
* **最近阶段的 rollout/export 没有使用 `llm` policy，也没有调用外部 API**

本次 review 请重点关注 correctness、leakage risk、data quality、training readiness，以及下一步应该做 GPU smoke training、继续扩充 SFT，还是优先做 pipeline hardening。

---

## 1. 当前状态

最新本地验证状态：

```text
active tasks: 100
planned backlog: 0
target total: 100

SFT total: 100
preference total: 169
preference bank total: 169
hard preference total: 64

make test: 103 passed
quality_gate.passed: true
quality_gate.errors: []
audit: PASS
p61-check: PASS
compileall: PASS
```

重要说明：

```text
p61_succeeded: False
```

目前理解为：这是 **重复运行 P61 脚本后的幂等性 false negative**，因为最终状态已经达成，重新运行时 delta counts 变成 0。请帮忙确认这里是否需要修复脚本逻辑。

---

## 2. 项目背景

本项目是 **CodeGuide-Agent**，定位为 verifier-driven code repair / coding-agent 数据集项目。

目标任务格式：

```text
issue + mini repository + public tests + hidden tests + gold.patch
```

期望 agent 输出：

```text
minimal patch + trajectory + reward / verifier result
```

当前已经实现的设计阶段：

1. Mini-Repo-Debug task construction。
2. Public / hidden test separation。
3. Gold patch verification。
4. Deterministic local rollout policies：`noop`、`heuristic`、`scripted`。
5. 从 weak / failed / no-op / original-buggy candidates 中挖掘 preference 数据。
6. Gold/reference SFT export：

   * `gold_patch_sft_candidate`
   * 明确标注为 reference supervised data，而不是 model-generated rollout。
7. HF-style training data build。
8. 对 model-facing artifacts 做 safety audit。

---

## 3. 近期重要里程碑

### P50-P54

P50 修复了 SFT 瓶颈。

在 P50 之前，SFT 一直停留在 19 条，因为只有 successful LLM rollout trajectories 才会被导出为 SFT。由于项目刻意避免使用 `llm` policy / API calls，本地 deterministic rollouts 只能产生 preference 数据，不能产生 successful patch trajectories。

P50 增加了一条安全的 gold/reference SFT 路径：

```text
record_type: gold_patch_sft_candidate
source: gold_patch
model-facing context: issue.md + public test command
supervised target: reference patch diff
excluded: hidden tests, hidden outputs, evaluator-only metadata, oracle actions
```

### P61-P100

P61 将数据集从 60 个 active tasks 扩展到 100 个 active tasks。

P61 后最终状态：

```text
active tasks: 100
planned backlog: 0
SFT: 100
preference: 169
hard preference: 64
```

P61 后发现并修复了一个关键问题：

* `validate_training_package()` 原本会把 empty rejected patches 判定为 invalid。
* 但 no-op / original-buggy rejected samples 本身是合法的 preference pairs：

  * chosen side = gold patch
  * rejected side = no change / buggy repo
  * public 可能通过，但 hidden 会失败
* 之后更新了 quality checker，使其满足：

  * chosen patch 必须有 valid diff；
  * 当 rejected patch 表示 no-op / original-buggy / no-patch behavior 时，允许为空；
  * quality gate 现在可以通过，并且不会丢弃 hard-preference records。

请 review 这套逻辑是否正确，以及 validation 是否应该写得更明确。

---

## 4. 建议 Review 的文件 / 目录

推荐 review bundle 包含：

```text
README.md
AGENTS.md
Makefile
pyproject.toml
requirements*.txt
configs/
codeguide_agent/
scripts/
tests/
docs/
data/mini_repo_debug/task_backlog.json
data/mini_repo_debug/repos/task_001/ ... task_100/
data/mini_repo_debug/exports/
data/mini_repo_debug/preference_bank/
data/mini_repo_debug/train_package/
data/mini_repo_debug/rollouts/*/summary.json
```

推荐排除：

```text
.git/
__pycache__/
*.pyc
data/mini_repo_debug/trajectories/
data/mini_repo_debug/hf_training/
large/generated caches
```

如果压缩包太大，可以保留全部 source code、tests、docs、training-package manifests，并选择一部分代表性任务，例如：

```text
task_001-task_010
task_041-task_050
task_061-task_070
task_091-task_100
```

但如果要做完整数据集 review，最好包含全部 100 个 task directories。

---

## 5. 主要 Review 问题

请按优先级回答以下问题。

### P0 — Correctness / Safety

1. hidden tests、hidden outputs、evaluator-only metadata 或 oracle actions 是否泄漏到了 model-facing SFT / preference / HF training artifacts 中？
2. gold/reference SFT export 是否安全，并且是否和 model-generated rollout data 清晰区分？
3. no-op / original-buggy rejected preference pairs 的 quality-gate 逻辑是否正确？
4. public / hidden test boundaries 在所有 task generation 和 export paths 中是否被严格遵守？
5. `gold.patch` 的验证强度是否足够？

### P1 — Dataset Quality

6. 这 100 个 tasks 是否足够多样，还是过于模板化？
7. P61 中 40/40 hard-pair tasks 是否真实可信，还是显得过于 synthetic？
8. 是否存在应该移除或去重的重复 task patterns？
9. reason labels / rejection reasons 对 DPO-style preference learning 是否足够有意义？
10. train/eval split 是否合适，是否存在 task-pattern leakage？

### P1 — Pipeline / Code Quality

11. export pipeline 是否过度耦合 generated artifacts？
12. `prepare_training_package.py` 是否承担了太多职责？
13. 是否应该统一 rollout/export scripts，而不是保留 P34/P38/P42/P50/P55/P61 多套脚本？
14. `make *-check` targets 对 CI 是否足够？
15. `p61_succeeded` 的 idempotency 逻辑是真问题，还是只是 cosmetic 问题？

### P2 — Training Readiness

16. 现在是否适合做 GPU smoke SFT？
17. 训练前是否应该先把 SFT 从 100 扩充到 150？
18. 下一步应该做：

    * smoke SFT only；
    * smoke DPO；
    * more gold/reference SFT；
    * small patch-capable rollout；
    * 还是先补更多 task diversity？
19. 当前数据规模是否足够支撑一个项目 demo？
20. 接下来最推荐的 3 个技术步骤是什么？

---

## 6. 当前本地已通过的命令

最新修复后，以下命令据报告已经通过：

```bash
python scripts/p61_repair_and_verify_tasks_061_100.py
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
make backlog-check
make docs-check
make canonical-check
make test
make clean-check
make audit
make scale-report
python scripts/p61_rollout_export_061_100.py
make p61-check
python -m compileall codeguide_agent
python -m codeguide_agent.training.build_hf_training_data --package data/mini_repo_debug/train_package --out data/mini_repo_debug/hf_training
```

已知的本地 Mac 限制：

```text
training-preflight 在 Mac 上返回 NOT_READY，因为当前本地没有训练依赖 / GPU。
这是预期行为。真实训练或 smoke training 应该在 GPU 机器上运行。
```

---

## 7. 期望的 Review 输出

请提供：

1. 总体判断：

   * ready for GPU smoke；
   * needs fixes before smoke；
   * 或 needs dataset hardening。
2. P0/P1/P2 issue list。
3. 具体到文件级别的修复建议。
4. no-op/original-buggy preference 逻辑是否可接受。
5. `gold_patch_sft_candidate` 作为 SFT 是否安全。
6. 现在是否应该开始训练，还是应该先继续扩充 SFT。
7. 推荐的下一步计划。

请避免泛泛而谈。请尽量基于这个仓库的实际设计和文件给出直接意见。
