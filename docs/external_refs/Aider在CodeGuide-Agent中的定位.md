# Aider 在 CodeGuide-Agent 中的定位：强 Baseline / Teacher / Repo-map & Edit-format 参考

> 目的：明确 Aider 不作为 CodeGuide-Agent 的主工程基座，而是作为成熟 AI Pair Programming 工具，在项目中承担 **强基线、教师数据来源、repo-map/edit-format 设计参考** 三类角色。  
> 推荐主基座：`forge-agent` 风格 runtime。  
> 推荐主贡献：CodeGuide-Agent 的 dataset、evaluation、reward、trajectory mining、training data pipeline。

---

## 1. 为什么不直接把 Aider 改造成 CodeGuide-Agent？

Aider 是一个非常成熟的终端 AI Pair Programming 产品，优势在于：

- repo map；
- 多模型接入；
- Git 集成；
- lint/test 自动修复；
- 多语言代码编辑；
- diff/edit format；
- 终端交互体验。

但 CodeGuide-Agent 的目标不是重新实现一个“更好用的终端编程助手”，而是构建一个面向代码模型能力提升的实验平台，核心关注：

- mini repo debug dataset；
- issue/repo 任务评测；
- gold file / gold function localization；
- patch minimality；
- no hard-code / no test deletion；
- process reward；
- trajectory → SFT/DPO/GRPO 数据构造；
- model weakness report；
- Code QA / Auto Repair / Vulnerability Detection 等多场景评测。

因此，Aider 适合做成熟基线和参考实现，不适合直接作为 CodeGuide-Agent 主体。否则项目容易被理解为“套壳 Aider”，你的研究贡献会被弱化。

---

## 2. Aider 在 CodeGuide-Agent 中的三类角色

### 2.1 Role 1：Strong Baseline

Aider 可以作为强基线，用于衡量 CodeGuide-Agent 的实际效果。

#### 用法

在同一批 mini repo debug tasks 上运行：

```text
Aider baseline
vs
forge-agent baseline
vs
CodeGuide-Agent
```

#### 评测指标

```text
Task Success Rate
Public Test Pass Rate
Hidden Test Pass Rate
Gold File Hit@K
Gold Function Hit@K
Patch Diff Size
No Hard-code Rate
No Test Deletion Rate
Regression Rate
Tool / Step Cost
```

#### 为什么重要

如果 CodeGuide-Agent 只和弱 baseline 比，面试时说服力不足。  
Aider 是成熟工具，拿它做 baseline，能证明你不是闭门造车。

---

### 2.2 Role 2：Teacher / Data Generator

Aider 可以作为 teacher，为 CodeGuide-Agent 生成候选修复轨迹或高质量 patch。

#### 数据生成流程

```text
mini repo task
→ Aider 尝试修复
→ run public/hidden tests
→ diff analyze
→ no hard-code / no test deletion verifier
→ 通过过滤的结果进入 teacher dataset
```

#### 产物

```text
successful patch
repair explanation
edit diff
test result
possible teacher trajectory
```

#### 用途

```text
SFT distillation data
DPO chosen samples
repair strategy examples
patch style examples
```

#### 注意

Aider 的输出不能直接全部作为训练数据，必须经过 verifier 过滤：

- 测试通过；
- patch diff 合理；
- 不删除测试；
- 不 hard-code；
- 不修改无关文件；
- 无 regression。

---

### 2.3 Role 3：Repo-map / Edit-format 参考

Aider 最值得借鉴的两个工程思想：

```text
1. Repo-map：如何在有限 token budget 中表示整个代码库结构；
2. Edit-format：如何让模型输出稳定、可解析、低 token 的代码修改。
```

#### Repo-map 参考方向

CodeGuide-Agent 可以借鉴：

```text
repo symbol extraction
function/class signature extraction
important file ranking
context budget allocation
issue-query related file selection
```

#### Edit-format 参考方向

CodeGuide-Agent 可以借鉴：

```text
diff-like edit format
search/replace block
whole-file fallback
patch apply failure recovery
minimal edit preference
```

#### 不建议直接复制的部分

除非 license 与工程兼容，否则不要直接复制 Aider 内部实现。  
建议优先学习设计思路，然后在 CodeGuide-Agent 中实现轻量版本。

---

## 3. Aider 和 forge-agent 的分工

| 模块 | Aider | forge-agent | CodeGuide-Agent 使用方式 |
|---|---|---|---|
| 终端 AI 编程体验 | 很强 | 中等 | Aider 做 baseline |
| Repo-map | 很强 | 有轻量 repo_map | 借鉴 Aider，结合 forge runtime |
| Edit format | 很成熟 | 基础工具式 edit | 借鉴 Aider 的 edit 思路 |
| ReAct runtime | 产品化，不以研究轨迹为核心 | 更清晰 | forge-agent 做主 runtime |
| Tool registry | 非项目主叙事 | 明确 | forge-agent 更适合改造 |
| Event log / trajectory | 需要额外提取 | JSONL event log 是一等模块 | forge-agent 更适合训练数据构造 |
| Dataset / eval / reward | 需要自己补 | 需要自己补 | CodeGuide-Agent 的核心贡献 |
| SFT/DPO/GRPO 数据构造 | 无 | 无 | CodeGuide-Agent 自己实现 |

推荐结论：

```text
forge-agent 负责 Agent 怎么跑；
Aider 负责成熟工具能做到什么水平；
CodeGuide-Agent 负责任务、评测、reward、数据和训练闭环。
```

---

## 4. CodeGuide-Agent 中推荐的目录设计

```text
CodeGuide-Agent/
  runtime/
    # 基于 forge-agent 风格改造
    agent/
    tools/
    context/
    llm/
    entry/

  baselines/
    aider_runner.py
    forge_runner.py

  datasets/
    mini_repo_debug/
    code_qa/
    vulnerability_lite/

  evaluators/
    localization_eval.py
    patch_eval.py
    qa_grounding_eval.py
    vuln_eval.py

  reward/
    process_reward.py
    outcome_reward.py
    rubric_reward.py

  data_builders/
    build_sft.py
    build_dpo.py
    build_grpo_rollouts.py

  docs/
    design_v0.6.md
    design_v0.7.md
    aider_baseline_teacher_reference.md
```

---

## 5. Aider Runner 的最小目标

实现一个 `baselines/aider_runner.py`，用于自动跑 Aider baseline。

### 输入

```json
{
  "task_id": "task_001",
  "repo_path": "data/mini_repo_debug/repos/task_001",
  "issue_path": "issue.md",
  "test_cmd": "pytest tests -q",
  "hidden_test_cmd": "pytest tests_hidden -q"
}
```

### 输出

```json
{
  "task_id": "task_001",
  "baseline": "aider",
  "status": "success_or_fail",
  "patch_diff": "...",
  "public_test_result": {},
  "hidden_test_result": {},
  "changed_files": [],
  "metrics": {
    "patch_size": 0,
    "no_test_deletion": true,
    "no_hardcode": true,
    "regression": false
  }
}
```

---

## 6. Aider Teacher 数据过滤规则

只有满足以下条件的 Aider 输出才能进入 teacher dataset：

```text
public tests pass
hidden tests pass
no test deletion
no hard-code
patch diff size within threshold
changed files intersect suspicious files or gold files
no unrelated file modifications
```

进入数据后，标记来源：

```json
{
  "source": "aider_teacher",
  "verified": true,
  "use_for": ["sft", "dpo_chosen"]
}
```

---

## 7. 面试讲法

> 我没有把 Aider 直接套壳成自己的项目。Aider 是成熟的终端 AI pair-programming 工具，所以我把它放在三个位置：第一，作为强 baseline，衡量我的 CodeGuide-Agent 在 mini repo debug tasks 上是否真的有收益；第二，作为 teacher，通过 verifier 过滤高质量 patch，生成蒸馏数据；第三，借鉴它的 repo-map 和 edit-format 思路，增强我的 repo navigation 和 minimal patch 能力。  
>
> CodeGuide-Agent 的核心贡献不在于重造一个 Aider，而在于构建代码任务数据集、process reward、patch verifier、trajectory mining，以及 SFT/DPO/GRPO 数据闭环。

---

## 8. 最终结论

Aider 的最佳定位：

```text
强 baseline
Teacher / data generator
Repo-map / edit-format reference
```

forge-agent 的最佳定位：

```text
主 runtime / scaffolding base
```

CodeGuide-Agent 的核心贡献：

```text
dataset
eval
reward
trajectory
training data pipeline
multi-scenario code intelligence evaluation
```
