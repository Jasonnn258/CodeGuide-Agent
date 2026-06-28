# CodeGuide-Agent 最终方案文档：100-Task v1 后的 Context / RAG / Training 路线

生成日期：2026-06-23

## 0. 一句话结论

CodeGuide-Agent 当前已经完成 **Mini-Repo-Debug v1 100-task 数据集里程碑**，下一阶段不应继续盲目扩 `task_101+`，也不应直接进入正式训练。正确路线是：

```text
冻结 100-task v1
-> 清理 rollout/export 脚本债务
-> GPU smoke SFT 验证训练链路
-> Context Management v0
-> ExperienceRecord / History RAG 离线设施与防泄漏测试
-> History RAG 接入 Agent Loop
-> Code RAG v0
-> SWE-bench Lite 外部评测适配
-> 再决定正式 SFT / DPO / RL
```

核心原则：

```text
正式训练要等，GPU smoke 要早做。
History RAG 的数据抽取是 P0，接入 agent loop 是 P1。
Context/RAG 之前，先把 phase scripts 统一，否则后续维护会爆炸。
任何 RAG / memory 设计必须先过防泄漏测试。
```

---

## 1. 当前项目状态

当前 CodeGuide-Agent 已完成 Mini-Repo-Debug v1：

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

当前尚未真实训练。Mac 本地训练环境缺少 GPU / torch / transformers / peft 等依赖，因此 `training-preflight` 在 Mac 上返回 `NOT_READY` 是正常的。

当前阶段成果可以表述为：

> CodeGuide-Agent 已完成 100-task Mini-Repo-Debug v1 数据集与训练包导出链路，SFT / preference / hard preference 数据均已生成并通过 quality gate 与 leakage audit。当前尚未进行正式训练，下一步是 GPU smoke training 与上下文/RAG 基础设施建设。

---

## 2. 已达成的关键共识

### 2.1 Smoke Training 的定义必须澄清

错误表述：

```text
跑 1 epoch smoke SFT
```

这容易被理解为真正开始训练模型。

正确表述：

```text
GPU smoke SFT = 训练链路连通性测试
```

目标只是验证：

```text
HF-style data 能否被 Trainer 读取
chat template / labels / EOS 是否正常
LoRA 配置是否可跑
forward / backward / optimizer step 是否正常
max_steps=3~10 后是否能保存 adapter
```

不看 loss 是否下降，不宣称模型能力提升，不作为最终训练结果。

推荐配置：

```text
max_steps: 3 或 10
小 batch
小 LoRA
只检查 adapter_config.json / logs / checkpoint 是否生成
```

---

### 2.2 History RAG 必须拆成两个阶段

不应直接把 History RAG 接入 agent loop。

正确拆分：

```text
P0：ExperienceRecord extractor + schema + leakage-safe retrieval tests + offline eval
P1：History RAG 接入 agent loop
```

原因：

```text
100 个任务来自生成式模板，存在 task_id 之外的模板级泄漏风险。
如果直接让 agent 检索历史任务，可能检索到同源模板的等价答案。
```

P0 只做离线设施，先保证不会污染。P1 再进入 agent prompt。

---

### 2.3 存储层与暴露层必须分离

不要说 “ExperienceRecord 不能存完整 diff”。更合理的是：

```text
存储层可以存 gold_patch / full diff
暴露给 agent 的 retrieval_view 不能包含 full diff
```

推荐 schema：

```json
{
  "experience_id": "task_076_gold_reference",
  "task_id": "task_076",
  "split": "train",
  "generator_family": "missing_helper_function",
  "patch_hash": "...",
  "issue_pattern_hash": "...",

  "storage_view": {
    "gold_patch": "diff --git ...",
    "negative_rollouts": []
  },

  "retrieval_view": {
    "issue_summary": "...",
    "failure_signal": "public passes but hidden import fails",
    "patch_summary": "add missing helper function",
    "changed_files": ["task_076_lib/validator.py"],
    "strategy": "inspect missing public API implied by issue/tests"
  },

  "visibility": {
    "allow_in_training": true,
    "allow_full_diff_in_retrieval_prompt": false
  }
}
```

---

### 2.4 防泄漏不能只按 task_id

最低限度要过滤：

```text
current_task_id
same split in evaluation mode
same generator_family
same patch_hash
same issue_pattern_hash
near-duplicate patch summary
```

否则可能出现：

```text
task_076 不检索 task_076，但检索到 task_096；
task_id 不同，但属于同一生成模板，patch 结构几乎相同。
```

这属于模板级泄漏。

---

### 2.5 Code RAG v0 不应一上来依赖 FAISS / Chroma

Code RAG 的第一版应采用 hybrid retrieval，而不是纯 embedding：

```text
BM25 / lexical score
+ AST chunk
+ path proximity
+ import relation
+ test mention relation
+ optional semantic score
```

原因：

```text
代码库中纯语义相似经常是噪声。
真正有用的是语义 + 结构 + 路径 + 调用关系的组合。
```

Embedding 可以作为 P1.5 ablation，不应作为 v0 的核心依赖。

---

## 3. 最终路线图

## P0：基础设施清偿与 Pipeline 验证

目标：

```text
冻结 100-task v1，清掉脚本债务，验证训练链路，建立上下文对象化和经验库防泄漏基础。
```

### P0-1：冻结 100-task v1

动作：

```bash
git status --short
git add Makefile codeguide_agent data/mini_repo_debug docs scripts tests
git commit -m "data: complete Mini-Repo-Debug 100-task dataset"
git push

git tag mini-repo-debug-v1-100tasks
git push origin mini-repo-debug-v1-100tasks
```

验收：

```text
make test: 103 passed
make audit: PASS
quality_gate.passed: true
scale-report:
  active tasks = 100
  planned backlog = 0
  SFT = 100
  preference = 169
  hard preference = 64
```

---

### P0-2：修复 p61_succeeded 幂等 false negative

当前现象：

```text
p61_succeeded: False
```

但：

```text
p61-check: PASS
quality_gate: passed true
SFT / preference / hard preference 达标
```

判断：

```text
这是重复运行后的幂等判断 false negative，不是数据失败。
```

修复原则：

```text
如果最终状态已达到 phase target，则 succeeded=true。
不要只看本次 delta 是否 > 0。
```

建议逻辑：

```python
p61_succeeded = (
    not failures
    and all(command_ok)
    and after["sft_total"] >= 100
    and after["preference_total"] >= 100
    and after["hard_preference_total"] >= 30
    and active_tasks == 100
    and planned_backlog == 0
)
```

---

### P0-3：统一 rollout/export phase scripts

当前债务：

```text
scripts/p34_rollout_export_021_025.py
scripts/p38_rollout_export_026_030.py
scripts/p42_rollout_export_031_040.py
scripts/p50_rollout_export_041_050.py
scripts/p55_rollout_export_051_060.py
scripts/p61_rollout_export_061_100.py
```

问题：

```text
每个 phase 都复制一套脚本。
后续加 Context/RAG 后，每个脚本都要改一遍，维护成本爆炸。
```

目标：

```text
抽象为一个统一 runner。
```

建议新增：

```text
scripts/run_bounded_rollout_export.py
scripts/check_bounded_rollout_export.py
```

命令形态：

```bash
python scripts/run_bounded_rollout_export.py \
  --task-start 61 \
  --task-end 100 \
  --phase p61 \
  --policies noop,heuristic,scripted \
  --root data/mini_repo_debug
```

验收：

```text
旧 p61 脚本可以变成 thin wrapper，或者被新脚本替代。
make p61-check 仍通过。
make test 仍通过。
```

---

### P0-4：GPU Smoke SFT

目标：

```text
验证训练链路，不验证模型效果。
```

GPU 机器上执行：

```bash
cd /path/to/CodeGuide-Agent

pip install -r requirements-training.txt

make training-data
make training-preflight
python -m codeguide_agent.training.real_sft_lora_train \
  --config configs/training/sft_smoke_tiny.json \
  --max-steps 3
```

验收标准：

```text
Trainer 不报错
能读取 sft_train / sft_eval
能完成 forward/backward
能保存 adapter_config.json
能保存训练日志
```

禁止事项：

```text
不看指标提升
不宣称模型变强
不发布 checkpoint 作为有效模型
```

---

### P0-5：Context Management v0

新增模块：

```text
codeguide_agent/context/
  __init__.py
  schemas.py
  manager.py
  budget.py
  compaction.py
  pack_builder.py
```

核心对象：

```text
ContextItem
ContextPack
ContextBudget
```

最小能力：

```text
将 issue / repo_map / retrieved files / test summary / recent tool trace 对象化
根据 token / char 预算选择上下文
压缩 run_test 长日志
保留 dropped context 的 reason
禁止 hidden / oracle 信息进入 prompt
```

验收测试：

```text
tests/test_context_pack.py
tests/test_context_compaction.py
tests/test_context_no_leakage.py
```

注：早期草案提到 `memory_store.py` 与 `ToolObservationSummary`，但 P0 范围内不落地 session/project memory store，tool trace 由 `ContextItem(role=TOOL_TRACE)` 承载，避免引入未使用的抽象。

---

### P0-6：ExperienceRecord extractor，不接入 Agent Loop

新增：

```text
codeguide_agent/rag/history_index.py
scripts/build_history_rag_index.py
scripts/eval_history_rag_retrieval.py
tests/test_history_experience_record.py
tests/test_history_rag_no_leakage.py
```

输入：

```text
data/mini_repo_debug/train_package/
data/mini_repo_debug/rollouts/*/summary.json
data/mini_repo_debug/repos/task_*/gold.patch
```

输出：

```text
data/mini_repo_debug/history_index/experience_records.jsonl
```

必须包含：

```text
task_id
split
generator_family
patch_hash
issue_pattern_hash
failure_signal
patch_summary
changed_files
negative_attempts
retrieval_view
storage_view
visibility
```

P0 阶段不允许：

```text
retrieve_history 直接接入 agent prompt
```

只做离线索引和防污染测试。

---

## P1：能力跃迁与真实对齐

目标：

```text
把 Context / History / Code RAG 接入实际 agent loop，并用真实基准检验。
```

### P1-1：History RAG 接入 Agent Loop

工具：

```text
retrieve_history(query, top_k, exclude_ids, exclude_family, exclude_hash)
```

暴露给 agent 的内容只能是：

```text
issue_summary
failure_signal
patch_summary
changed_files
strategy
negative_attempt_summary
```

禁止：

```text
current task gold patch
hidden tests
hidden outputs
full diff
same family / same patch hash 样本
```

评估指标：

```text
top-k same-pattern retrieval accuracy
localization top-k accuracy
tool step count 是否下降
public-pass-hidden-fail 修复率是否提升
最终 patch pass rate 是否提升
```

---

### P1-2：Code RAG v0

新增：

```text
codeguide_agent/rag/chunking.py
codeguide_agent/rag/code_index.py
codeguide_agent/rag/retriever.py
codeguide_agent/tools/semantic_search_repo.py
scripts/build_code_rag_index.py
scripts/eval_rag_localization.py
```

v0 不直接上纯 embedding，而是：

```text
BM25 / lexical
+ AST function/class chunk
+ path proximity
+ import relation
+ test mention relation
+ optional semantic score
```

与现有工具关系：

```text
search_repo：精确关键词 / regex 主力工具
semantic_search_repo：自然语言意图检索 / fallback / exploration
```

---

### P1-3：SWE-bench Lite Eval Adapter

目标：

```text
接入 3~10 个 SWE-bench Lite / Verified 真实任务，只做 evaluation。
```

不做：

```text
不混入训练
不直接做正式 SFT
不宣称 benchmark 成绩
```

要跑通：

```text
repo setup
issue ingestion
patch output
test command wrapper
result schema
```

作用：

```text
暴露真实大仓库下的 context explosion / retrieval noise / dependency setup 问题。
```

---

## P2：长期演进与规模扩张

### P2-1：API Docs RAG

先做 allowlist + cache：

```text
stdlib
pytest
requests
click
pydantic
fastapi
sqlalchemy
pandas
```

不建议第一版开放任意联网抓文档。

---

### P2-2：SWE-smith 风格任务生成器

目标：

```text
从真实 Python repo 自动生成 mini/SWE-style repair tasks。
```

用途：

```text
将数据规模从 100 扩展到 1k+
增加真实 repo diversity
减少当前 synthetic template 偏差
```

---

### P2-3：正式训练

前置条件：

```text
Context/RAG 稳定
leakage audit 稳定
SWE-bench Lite adapter 跑通
SFT 至少 150+，更理想是 1k+
preference / hard preference 继续扩充
```

训练路线：

```text
SFT
DPO smoke
DPO / GRPO toy
正式 agentic RL
```

---

## 4. 风险清单与防线

### 风险 1：非官方 Claude Code 镜像源码合规风险

结论：

```text
不复制、不改写、不 vendor。
只参考官方文档和公开架构思想。
```

---

### 风险 2：RAG 噪声误导模型

防线：

```text
RAG snippet 有严格 token budget
RAG 结果进入 ContextPack 前必须 rerank
保留 search_repo 作为精确检索主力
semantic_search_repo 作为辅助工具
```

---

### 风险 3：History RAG 泄漏

防线：

```text
exclude current_task_id
exclude same generator_family
exclude same patch_hash
exclude same issue_pattern_hash
eval set 与 history index 隔离
retrieval_view 不暴露 full diff
```

---

### 风险 4：100-task 数据过于 synthetic

结论：

```text
100-task v1 适合验证 pipeline 和防泄漏，不足以证明真实 repo 泛化。
```

对策：

```text
尽快做 SWE-bench Lite eval adapter。
```

---

### 风险 5：SFT=100 不足以正式训练

结论：

```text
只能 smoke，不能正式训练。
```

对策：

```text
max_steps=3~10
只验证 trainer 链路
不声明模型效果
```

---

## 5. 验收标准总表

### P0 完成标准

```text
100-task v1 committed and tagged
p61_succeeded 幂等 false negative 修复
unified bounded rollout/export runner 可替代 phase scripts
GPU smoke SFT max_steps=3 通过
ContextPack v0 tests 通过
ExperienceRecord extractor 生成 history_index
history leakage tests 通过
make test / audit / scale-report 全绿
```

### P1 完成标准

```text
History RAG 接入 agent loop
History RAG ablation 有离线指标
Code RAG v0 支持 hybrid retrieval
semantic_search_repo 可用
SWE-bench Lite 3~10 task adapter 跑通
```

### P2 完成标准

```text
API Docs RAG allowlist 可用
SWE-smith style generator 原型可用
dataset 扩展到 1k+
正式训练前置条件满足
```

---

## 6. 最终执行顺序

严格按以下顺序推进：

```text
1. commit + tag 100-task v1
2. 修 p61_succeeded 幂等判断
3. 统一 rollout/export scripts
4. GPU smoke SFT，max_steps=3~10
5. Context Management v0
6. ExperienceRecord extractor + 防泄漏测试
7. History RAG offline eval
8. History RAG 接入 agent loop
9. Code RAG v0
10. SWE-bench Lite eval adapter
11. 再考虑更多数据与正式训练
```

---

## 7. 最终建议

当前不要继续扩 `task_101+`，也不要直接正式训练。

最优路线是：

```text
先把 100-task v1 固化成稳定里程碑，
再用 GPU smoke 验证训练链路，
然后清理脚本债务与上下文管理问题，
最后再进入 RAG 与真实 SWE-bench 对齐。
```

这条路线的核心价值是：

```text
不急着堆模型效果，
而是先把 verifier-driven coding-agent pipeline 做成一个可复现、可审计、可扩展的系统。
```
