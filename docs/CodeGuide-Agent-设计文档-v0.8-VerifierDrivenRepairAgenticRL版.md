# CodeGuide-Agent 设计文档 v0.8：Verifier-Driven Code Repair Agentic RL 主线收敛版

> Repo：`https://github.com/Jasonnn258/CodeGuide-Agent`  
> 当前定位：**以可验证执行反馈驱动的代码修复 Agentic RL 项目**。  
> 核心主线：不再做“五个代码场景齐头并进”，而是把 **Auto Repair / Repo-level Debugging** 作为唯一主线做深；Code QA + RAG 作为次线；漏洞检测 Lite 作为轻量泛化验证；IDE Completion、VLM、通用 Multi-Agent 暂时不进入 MVP。  
> 关键词：**Mini-Repo-Debug、Tool Use、Verifier Reward、SFT、Knowledge Distillation、GRPO、Reward Hacking 防范、Process Reward、Code QA RAG**。

---

## 0. v0.8 版本变更说明

v0.7 的问题是：为了对齐字节 JD，把 IDE 补全、代码 QA、场景化 Agent、自动修复、漏洞检测都展开成完整场景，导致项目看起来像“五个浅 demo 拼盘”。

v0.8 进行核心收缩：

```text
v0.7:
多场景 Code Intelligence 系统
IDE Completion / Code QA / Agent / Repair / Vulnerability 并列

v0.8:
一深四浅
Auto Repair / Agentic RL 是唯一主线
Code QA + RAG 是次线
Vulnerability Lite 是轻量验证
IDE Completion / VLM / 通用 Multi-Agent 只做展望
```

本次改动遵循一个原则：

> **能用 verifier 产生可靠 reward 的任务，才适合作为 Agentic RL 主线。**

因此，自动修复是主线；代码 QA 适合 SFT / 蒸馏 / DPO；漏洞检测适合规则 verifier 的轻量评测；IDE 补全与 VLM 暂时不投入主工程。

---

## 1. 项目一句话

**CodeGuide-Agent v0.8 是一个以可验证执行反馈驱动的代码修复 Agentic RL 项目。它围绕 Mini-Repo-Debug 任务构建代码上下文检索、工具执行、测试验证、轨迹记录和 reward 系统，通过 SFT、知识蒸馏和 GRPO 优化模型在 repo-level debugging / auto repair 场景下的搜索、定位、修复和测试反馈利用能力。**

---

## 2. 与原 CodeGuide-LLM 的继承关系

### 2.1 原 CodeGuide-LLM

原项目是：

```text
算法题 → 教学题解
```

核心能力：

```text
题意理解
算法推导
代码生成
复杂度分析
教学解释
GRPO / Reward / Ablation 经验
```

### 2.2 CodeGuide-Agent v0.8

新项目是：

```text
Issue + Mini Repo + Failing Tests
→ repo navigation
→ fault localization
→ minimal patch
→ run tests
→ repair trajectory
→ verifier reward
→ SFT / Distillation / GRPO
```

继承关系：

| 原 CodeGuide-LLM 资产 | v0.8 中的用途 |
|---|---|
| 算法题教学数据 | Code QA / explanation 蒸馏次线 |
| QLoRA / GRPO 经验 | Agentic RL 主线 |
| Accuracy / Format / Teaching Reward 经验 | Reward 归一化、reward hacking 防范经验 |
| 评测与 ablation 习惯 | baseline → SFT → distill → GRPO 阶梯实验 |

一句话：

> CodeGuide-LLM 是 response-level coding tutor；CodeGuide-Agent 是 verifier-driven coding repair agent。

---

## 3. 项目边界：一深四浅

### 3.1 一深：Auto Repair / Agentic RL

唯一主线：

```text
Mini Repo Debug
→ Tool Use
→ Verifier Reward
→ Repair Trajectory
→ SFT / Distillation / GRPO
```

必须真的实现和实验。

### 3.2 次线：Code QA + RAG

轻量实现：

```text
CodeGuide-LLM QA 数据
+ repo grounding
+ hybrid retrieval
+ grounded answer evaluation
```

作用：

```text
复用原项目资产
证明共享底座可迁移
用 DPO 处理非 verifier 偏好
```

### 3.3 轻量验证：Vulnerability Lite

只做 eval，不训练闭环：

```text
10-20 个注入漏洞正样本
10-20 个无漏洞负样本
规则 verifier
FPR / TPR / line hit
```

### 3.4 展望：IDE Completion / VLM / 通用 Multi-Agent

不进 MVP：

```text
IDE Completion:
需要 FIM / 低延迟 / 接受率评测，和当前 Agentic RL 主线弱相关。

VLM:
暂不做截图/IDE UI 理解，避免 headline 与实现不匹配。

通用 Multi-Agent:
不做多个 agent 互聊。只在后期做“定位角色 vs patch 角色”的轻量 ablation。
```

---

## 4. 总体架构

```text
Mini Repo Debug Task
        │
        ▼
Task Loader
issue.md / repo / public tests / hidden tests / metadata
        │
        ▼
Shared Tool Layer
repo_tree / search_repo / read_file / edit_file / run_test / git_diff / rollback
        │
        ▼
Repair Agent Policy
search → read → localize → patch → test → revise / stop
        │
        ▼
Verifier & Reward
fail-to-pass / pass-to-pass / patch minimality / grounding / tool cost
        │
        ▼
Trajectory Logger
action-observation trace / patch diff / test logs / reward components
        │
        ▼
Training Data Builder
SFT trajectories / distilled rationales / GRPO rollout groups
        │
        ▼
Training
QLoRA SFT → Distillation SFT → Agentic GRPO
        │
        ▼
Evaluation Report
repair success / tool efficiency / reward hacking cases / ablation
```

---

## 5. 核心任务：Auto Repair / Mini-Repo-Debug

### 5.1 任务定义

输入：

```json
{
  "task_id": "task_001",
  "issue": {
    "title": "YAML config is not supported by CLI",
    "body": "JSON config works, but passing config.yaml crashes. README says YAML config should work."
  },
  "repo_path": "data/mini_repo_debug/repos/task_001",
  "public_test_cmd": "pytest tests -q",
  "hidden_test_cmd": "pytest tests_hidden -q"
}
```

Agent 动作：

```text
repo_tree
search_repo
read_file
edit_file
run_test
git_diff
rollback
stop
```

输出：

```json
{
  "topk_suspicious_files": ["src/config_loader.py"],
  "topk_suspicious_functions": ["load_config"],
  "root_cause": "load_config always uses json.loads and does not branch on .yaml/.yml files.",
  "patch_diff": "...",
  "test_result": {
    "public_pass": true,
    "hidden_pass": true,
    "regression": false
  }
}
```

---

## 6. Mini-Repo-Debug 数据集设计

### 6.1 目标规模

第一版目标：

```text
总任务数：80-120
训练集：70-90
验证集：10-15
测试集：10-15
每个 repo：5-20 个文件
每个 repo：100-800 行代码
每个任务：1 个 issue、1 个 gold patch、1-2 个 gold files、1-3 个 gold functions
```

### 6.2 任务类型分布

| 类型 | 数量目标 | 例子 |
|---|---:|---|
| Parser / Config | 15-20 | JSON/YAML/TOML、缺省字段、空输入 |
| CLI Argument | 10-15 | bool flag 反了、默认值覆盖用户输入 |
| Data Processing | 10-15 | CSV header、空行、类型转换 |
| Cache / State | 10-15 | cache key 缺参数、状态污染 |
| File / Path I/O | 10-15 | expanduser、相对路径、文件不存在 |
| Cross-file Call Chain | 15-20 | CLI → service → parser 下游错误 |
| Runtime / Exception | 5-10 | None、越界、异常处理 |
| Hidden Regression | 5-10 | public 过但 hidden 挂 |

### 6.3 数据目录

```text
data/mini_repo_debug/
  tasks.jsonl
  repos/
    task_001/
      issue.md
      README.md
      pyproject.toml
      src/
      tests/
      tests_hidden/
      metadata.json
      gold.patch
```

### 6.4 metadata schema

```json
{
  "task_id": "task_001",
  "scenario": "auto_repair",
  "bug_type": "parser_config",
  "difficulty": "easy",
  "repo_path": "data/mini_repo_debug/repos/task_001",
  "issue_path": "issue.md",
  "gold_files": ["src/config_loader.py"],
  "gold_functions": ["load_config"],
  "gold_patch": "gold.patch",
  "public_test_cmd": "pytest tests -q",
  "hidden_test_cmd": "pytest tests_hidden -q",
  "forbidden_behaviors": [
    "delete_tests",
    "hardcode_expected_output",
    "modify_unrelated_files"
  ],
  "source": "handcrafted",
  "split": "train"
}
```

### 6.5 任务验证规则

每个任务必须满足：

```text
clean version public + hidden pass
buggy version 至少一个 public 或 hidden fail
gold patch 后 public + hidden pass
gold patch changed files <= 2
gold patch changed lines <= 30
issue 不直接暴露 gold file 和 exact fix
```

---

## 7. 共享工具层

### 7.1 必做工具

| Tool | 作用 | Verifier / Reward 信号 |
|---|---|---|
| `repo_tree` | 查看项目结构 | 是否快速定位相关目录 |
| `search_repo` | grep/rg 搜索 | gold file hit、重复搜索惩罚 |
| `read_file` | 读取文件片段 | opened file 数量、evidence |
| `edit_file` | 结构化修改文件 | patch diff |
| `run_test` | 运行 public/hidden tests | fail-to-pass、pass-to-pass |
| `git_diff` | 查看修改 | patch minimality |
| `rollback` | 回滚失败 patch | regression 防范 |
| `trajectory_log` | 记录轨迹 | SFT / GRPO 数据来源 |

### 7.2 Tool schema 示例

```json
{
  "action_name": "search_repo",
  "action_input": {
    "query": "load_config yaml",
    "path": ".",
    "file_glob": "*.py"
  }
}
```

Observation：

```json
{
  "tool_name": "search_repo",
  "status": "success",
  "matches": [
    {
      "file": "src/config_loader.py",
      "line": 12,
      "text": "def load_config(path):"
    }
  ]
}
```

---

## 8. Repair 轨迹样本 schema

### 8.1 trajectory schema

```json
{
  "trajectory_id": "traj_000001",
  "task_id": "task_001",
  "model": "qwen2.5-coder-7b-sft",
  "steps": [
    {
      "step_id": 1,
      "thought": "Issue mentions YAML config, search for config loading code.",
      "action_name": "search_repo",
      "action_input": {
        "query": "config yaml load_config"
      },
      "observation": {
        "matches": ["src/config_loader.py:12:def load_config(path):"]
      }
    }
  ],
  "final_patch": "...",
  "reward": {
    "R_outcome": 1.0,
    "R_process": 0.7,
    "P_tool_cost": -0.1
  },
  "final_status": "success"
}
```

### 8.2 SFT 样本

```json
{
  "messages": [
    {"role": "system", "content": "You are CodeGuide-Agent, a repo-level code repair agent."},
    {"role": "user", "content": "<issue>...</issue><repo_summary>...</repo_summary>"},
    {"role": "assistant", "content": "<action>{...}</action>"},
    {"role": "tool", "content": "<observation>{...}</observation>"},
    {"role": "assistant", "content": "<final_patch>...</final_patch>"}
  ],
  "metadata": {
    "task_id": "task_001",
    "source": "distilled_success_trajectory"
  }
}
```

### 8.3 GRPO rollout group

```json
{
  "task_id": "task_001",
  "rollouts": [
    {"trajectory_id": "traj_a", "reward": 0.91, "final_status": "success"},
    {"trajectory_id": "traj_b", "reward": 0.42, "final_status": "partial"},
    {"trajectory_id": "traj_c", "reward": -0.10, "final_status": "regression"},
    {"trajectory_id": "traj_d", "reward": 0.00, "final_status": "fail"}
  ]
}
```

---

## 9. 训练方法选择边界

| 方法 | 用在哪里 | 不用在哪里 | 原因 |
|---|---|---|---|
| SFT | 工具调用格式、成功 repair 轨迹、QA 格式 | 不能直接保证测试通过 | 学行为模板 |
| 知识蒸馏 | 强模型生成 root cause、evidence、patch rationale | 不能替代 verifier | 让小模型学高质量中间过程 |
| DPO | Code QA 的简洁/grounded 偏好 | Repair 的 test pass/no regression | QA 偏主观；Repair 有 verifier，直接用 RL 更高效 |
| GRPO | Auto Repair 的多轨迹优化 | QA 主观回答 | Repair 有 outcome/process reward，可做 group-relative 优化 |
| LLM Judge | QA 质量、解释质量辅助评估 | test pass/fail、文件引用存在性 | 能程序判断的不用 judge |

关键边界：

> **Repair 场景不用 DPO 包装 test pass/no regression 这种可验证信号，直接进入 GRPO reward。  
> DPO 只用于没有可靠 verifier 的 QA 偏好场景。**

---

## 10. Reward System v2

### 10.1 Reward 总公式

```text
R_total =
  0.45 * R_outcome
+ 0.25 * R_process
+ 0.15 * R_patch_safety
+ 0.10 * R_grounding
+ 0.05 * R_efficiency
- 0.30 * P_regression
- 0.25 * P_hardcode
- 0.20 * P_test_deletion
```

### 10.2 R_outcome

```text
public tests pass: +0.4
hidden tests pass: +0.6
partial pass: pass_ratio * 0.5
```

### 10.3 R_process

```text
gold file hit@3: +0.25
gold function hit@3: +0.25
failure count decreases after patch: +0.25
correct stop after pass: +0.15
rollback after regression: +0.10
```

### 10.4 R_patch_safety

```text
changed files <= 2: +0.3
changed lines <= 30: +0.3
no test files modified: +0.2
no unrelated files modified: +0.2
```

### 10.5 R_grounding

尽量程序化，不依赖 LLM judge：

```text
引用文件存在: +0.25
引用 symbol 存在: +0.25
引用 line range 合法: +0.25
root cause evidence 来自 opened files 或 test logs: +0.25
```

### 10.6 R_efficiency

```text
tool calls <= 8: +0.4
duplicate search <= 1: +0.2
opened irrelevant files <= 2: +0.2
final answer length within budget: +0.2
```

### 10.7 Penalty

```text
P_regression:
修复后原通过测试失败，强惩罚。

P_hardcode:
patch 中出现明显针对测试输入/输出的硬编码，强惩罚。

P_test_deletion:
修改或删除 tests/ 文件，强惩罚。

P_unrelated_edit:
修改不在 suspicious files 或 gold file 相关范围内的文件，惩罚。

P_tool_loop:
重复执行相同无收益工具调用，惩罚。
```

### 10.8 Reward 归一化

每条 trajectory 先得到 raw reward，再在同一 task 的 group 内做归一化：

```text
adv_i = (r_i - mean(r_group)) / (std(r_group) + 1e-6)
```

如果 group 内所有 reward 相同：

```text
使用历史 moving baseline 或跳过该 group，避免 advantage 全 0。
```

---

## 11. Reward Hacking 防范

### 11.1 典型 hacking case

| Hacking | 表现 | 防范 |
|---|---|---|
| 删除测试 | 直接让 pytest 不执行失败测试 | P_test_deletion |
| Hard-code | 针对 public test 输入写 if 分支 | P_hardcode + hidden tests |
| 大范围重构 | 通过重写绕过 bug，但引入风险 | patch minimality penalty |
| 不跑测试就声称通过 | final_status 与工具日志不一致 | trajectory verifier |
| 只过 public 不管 hidden | public pass 但 hidden fail | hidden outcome reward |
| 乱搜堆上下文 | 打开大量无关文件 | tool cost + irrelevant file penalty |

### 11.2 监控指标

```text
test_file_modified_rate
hardcode_flag_rate
avg_changed_lines
avg_tool_calls
reward_mean / reward_std
success_rate
regression_rate
output_length
repetition_rate
KL to reference model
```

---

## 12. Policy Collapse 监控

GRPO 训练中监控：

```text
1. 平均输出长度是否异常增长；
2. action 分布是否塌缩到只 run_test 或只 edit；
3. tool call 数是否持续上升；
4. reward 方差是否接近 0；
5. KL 是否过大；
6. success rate 是否上升但 hidden pass 不升；
7. hardcode rate 是否上升。
```

Checkpoint 选择：

```text
不只选 train reward 最高；
优先选 val hidden pass 高、regression 低、hardcode 低、tool cost 低的 checkpoint。
```

---

## 13. Code QA + 轻量 RAG 次线

### 13.1 定位

Code QA 不作为 RL 主线。

它的作用：

```text
复用 CodeGuide-LLM 数据资产；
证明共享 repo context engine 可迁移；
用 RAG 降低 hallucination，提高 grounding。
```

### 13.2 数据规模

```text
QA SFT 数据：500-1000 条
来源：
- CodeGuide-LLM 原教学数据改写
- Mini repo 中函数解释 / bug explanation
- 强模型蒸馏生成 repo-grounded QA
```

### 13.3 RAG

检索对象：

```text
文件片段
函数定义
docstring
README
测试片段
```

召回方式：

```text
BM25 + 向量检索 hybrid
Top-k = 3-5
```

### 13.4 DPO 使用场景

DPO 用于：

```text
grounded answer > hallucinated answer
简洁正确解释 > 啰嗦泛泛解释
引用真实文件/函数 > 不引用证据
```

不用于：

```text
test pass/no regression 这类 verifier reward
```

---

## 14. Vulnerability Detection Lite

### 14.1 定位

只做轻量 eval，不进入主训练闭环。

### 14.2 数据规模

```text
正样本：10-20 个人工注入漏洞
负样本：10-20 个对应 clean / no-vuln 样本
```

### 14.3 漏洞类型

```text
命令注入
路径穿越
SQL 字符串拼接
硬编码密钥
不安全反序列化
```

### 14.4 评测

```text
TPR / FPR
line-level hit
vulnerability type accuracy
fix suggestion correctness
security rule pass
functionality regression rate
```

关键补充：

> 没有负样本不能测 FPR，因此漏洞检测 Lite 必须包含 clean negative examples。

---

## 15. 不进入 MVP 的方向

### 15.1 IDE Completion

暂不做完整训练链路。

原因：

```text
需要 FIM 数据、低延迟推理、接受率评测；
与 Agentic RL 主线弱相关。
```

最多做：

```text
文档化 FIM 数据构造方案。
```

### 15.2 VLM

从 headline 移除。

原因：

```text
当前没有 IDE 截图、终端截图、UI 任务数据；
VLM 会稀释代码主线。
```

保留为：

```text
未来可用于 IDE screenshot / terminal screenshot understanding。
```

### 15.3 通用 Multi-Agent

不做通用多智能体框架。

后置可做轻量 ablation：

```text
Single Agent:
定位 + patch 混合在一个 policy 中。

Two-role Agent:
Locator 负责 repo navigation / root cause；
Patcher 负责 diff 生成。

比较：
gold file hit、repair success、tool cost。
```

---

## 16. 实验阶梯设计

这是面试故事核心。

### 16.1 Baselines

```text
B0: Prompt-only base model
B1: Strong model prompt-only
B2: Rule/tool-only baseline
```

### 16.2 训练阶梯

```text
M0: Qwen2.5-Coder base
M1: + SFT successful trajectories
M2: + Distilled root cause / evidence / patch rationale
M3: + GRPO verifier reward
```

### 16.3 必做对比

| 对比 | 证明什么 |
|---|---|
| M1 vs M0 | SFT 学到工具调用格式和 repair 轨迹 |
| M2 vs M1 | 蒸馏中间过程提升 root cause 和 evidence |
| M3 vs M2 | GRPO 优化 test-feedback repair 策略 |
| M3 vs strong prompt-only | 小模型可控性/成本/可训练闭环价值 |
| with RAG vs without RAG in QA | RAG 降低 hallucination |
| vuln positive-only vs pos+neg | 负样本对 FPR 评测必要 |

---

## 17. 训练配置与资源估计

### 17.1 数据规模

```text
Mini-Repo-Debug tasks: 80-120
Distilled repair trajectories: 300-800
QA grounded SFT samples: 500-1000
GRPO rollout tasks: 50-100
Rollouts per task: group size 4-8
Vulnerability Lite: 20-40 samples total
```

### 17.2 模型配置

优先级：

```text
Fast dev:
Qwen2.5-Coder-1.5B / 3B

Main experiment:
Qwen2.5-Coder-7B-Instruct + QLoRA

Fallback:
如果 7B GRPO 不稳定，GRPO 用 3B 做 proof-of-concept。
```

### 17.3 训练配置建议

SFT：

```text
model: Qwen2.5-Coder-7B-Instruct
method: QLoRA
epochs: 1-3
seq_len: 4096-8192
gpu: 1-2 × 3090
```

GRPO：

```text
model: 3B or 7B QLoRA adapter
tasks: 50-100
group_size: 4-8
steps: 200-500
max_tool_steps: 8
gpu: 2-4 × 3090 if available
```

现实约束：

```text
6 张 3090 非独占，按稳定 1-2 张卡规划；
多卡 GRPO 只作为空闲时 proof-of-concept。
```

---

## 18. 四阶段工程路线图

### Phase 1：共享底座 + 主线数据

时间：1-2 周  
GPU：不需要

交付物：

```text
repo navigation tools
verifier framework
Mini-Repo-Debug 80-120 tasks
trajectory logger
reward calculator v1
prompt-only baseline eval
```

指标：

```text
base repair success
gold_file_hit@3
avg_tool_calls
public/hidden pass
```

面试展示：

```text
我从零构建了可验证执行环境和 reward 计算框架。
```

---

### Phase 2：SFT + 蒸馏

时间：1-2 周  
GPU：1-2 × 3090 + API

交付物：

```text
300-800 repair trajectories
500-1000 QA samples
Qwen2.5-Coder-7B QLoRA SFT
with/without distillation ablation
```

指标：

```text
repair success
root cause accuracy
evidence grounding
QA grounding
```

面试展示：

```text
SFT 学轨迹格式，蒸馏提升 root cause 和 evidence。
```

---

### Phase 3：Agentic GRPO

时间：1-2 周  
GPU：2-4 × 3090 空闲时；不稳定则 3B 模型

交付物：

```text
GRPO rollout groups
reward normalization
collapse monitoring
SFT+distill+GRPO checkpoint
```

指标：

```text
repair success
fail-to-pass
pass-to-pass
avg repair steps
tool cost
hardcode rate
regression rate
```

面试展示：

```text
GRPO 不是堆关键词，而是用 verifier reward 优化 test-feedback repair 策略。
```

---

### Phase 4：轻量泛化验证 + 收尾

时间：1 周  
GPU：可选

交付物：

```text
Code QA + RAG
Vulnerability Lite pos/neg eval
2-3 SWE-bench Lite sanity tasks
README / report / interview story
```

指标：

```text
QA grounding rate
vuln TPR/FPR
SWE-bench sanity pass/fail
```

面试展示：

```text
主线做深，次线证明共享底座可迁移。
```

---

## 19. 面试故事

> 我最开始做 CodeGuide-LLM，是一个 response-level 的算法题教学模型。后来我发现，如果要对齐代码大模型训练优化岗位，不能把项目做成五个代码应用 demo 的拼盘，而要选一个有可验证 reward、能闭环训练的场景做深。  
>
> 所以我把 CodeGuide-Agent 收敛成 verifier-driven code repair agent。核心任务是 Mini-Repo-Debug：给定 issue 和小型 repo，模型需要 search/read/edit/run test，找到相关文件和函数，做最小 patch，并通过测试反馈持续修复。这个场景天然有 fail-to-pass、pass-to-pass、patch minimality 等 verifier reward，适合做 Agentic GRPO。  
>
> 训练上，我分三步：先用 SFT 让模型学会工具调用和修复轨迹；再用强模型蒸馏 root cause、evidence summary 和 patch rationale；最后用 GRPO 在同一任务的多条 repair trajectory 上做 group-relative 优化。Code QA 和漏洞检测只做轻量验证，用来说明共享底座可以迁移，但不抢主线。  
>
> 这样项目的重点不是“我做了很多场景”，而是“我把 SFT、蒸馏、GRPO 这条后训练链路，在一个真实可执行、可验证的代码修复场景里跑通”。

---

## 20. 面试质疑与回答

### Q1：为什么不做五个场景？

答：

```text
字节 JD 的五个场景是例子，不是任务清单。
我选择 Auto Repair 做深，因为它有最可靠的 verifier reward，天然适合 Agentic RL。
其他场景做轻量验证，避免项目变成五个浅 demo。
```

### Q2：为什么 Repair 用 GRPO，不用 DPO？

答：

```text
Repair 有明确 verifier reward，比如 tests pass、no regression、patch minimality。
这种信号直接进入 GRPO 更合适。
DPO 更适合 QA 这类主观偏好任务，比如 grounded answer > hallucinated answer。
```

### Q3：reward 会不会被 hack？

答：

```text
会，所以我显式设计了 test deletion、hard-code、大范围重构、public-only overfit、regression 等检测。
并且 checkpoint 不只看 train reward，而看 hidden pass、regression、hardcode rate 和 tool cost。
```

### Q4：Mini-Repo-Debug 会不会不真实？

答：

```text
会有分布局限。
所以我把它作为可控主数据源，保证 gold file/function/reward 可标注。
再用 2-3 个 SWE-bench Lite 任务做真实性 sanity check，不追求大规模 leaderboard。
```

### Q5：为什么不直接 prompt 强模型？

答：

```text
强模型是 baseline。
项目目标不是证明小模型绝对超过强模型，而是证明在可控任务分布上，通过 SFT+蒸馏+GRPO，小模型能逼近强模型，同时具备更低成本、更可控的工具策略和可持续训练闭环。
```

---

## 21. 删除 / 保留 / 新增 / 后置

| 条目 | 处理 | 说明 |
|---|---|---|
| Auto Repair / Agentic GRPO | 保留并加强 | 唯一主线 |
| Mini-Repo-Debug | 保留并扩展 | 目标 80-120 tasks |
| Code QA + RAG | 新增为次线 | SFT/DPO 场景，不抢 RL 主线 |
| Vulnerability Lite | 保留轻量 eval | 必须补负样本，能测 FPR |
| IDE Completion 完整链路 | 后置 | 不进 MVP |
| VLM | 从 headline 删除 | 只在展望提一句 |
| 通用 Multi-Agent | 删除 | 避免过度工程 |
| Two-role Locator/Patcher | 后置 | Phase 4 ablation |
| Repair 场景 DPO | 删除 | verifier reward 直接做 GRPO |
| QA 场景 DPO | 新增 | grounded vs hallucinated |
| Reward 公式清单 | 重做 | 加权重、归一化、hacking 防范 |
| 数据 schema | 新增 | 每类样本 JSON 示例 |
| GRPO 配置数字 | 新增 | group size、steps、模型、GPU |

---

## 22. 结论

v0.8 的核心判断：

> 项目不要靠覆盖五个场景显得“大”，而要靠一个可验证主线做深。  
> Auto Repair 是最适合作为主线的代码场景，因为它天然拥有 verifier reward，能承载 SFT、知识蒸馏和 Agentic GRPO 的完整训练故事。  
> Code QA 和漏洞检测作为轻量扩展即可；IDE、VLM、通用 Multi-Agent 不进入当前实现范围。

最终定位：

```text
CodeGuide-Agent:
Verifier-Driven Code Repair Agentic RL System
```
