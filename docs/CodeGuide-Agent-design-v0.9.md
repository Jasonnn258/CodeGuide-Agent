# CodeGuide-Agent v0.9：Executable Rollout & Reward Hardening for Verifier-Driven Code Repair

> Repo: `https://github.com/Jasonnn258/CodeGuide-Agent`  
> 当前定位：**Executable Verifier-Driven Code Repair Agentic RL System**  
> 主线：Mini-Repo-Debug / repo-level debugging / auto repair  
> 版本目标：在 v0.8 “主线收敛”基础上，把 **rollout 执行协议、reward 程序化规则、trajectory-to-training-data 路径、compute budget 与面试防守点** 补成可执行设计。

---

## 0. 为什么需要 v0.9？

v0.8 的方向已经正确：Auto Repair / Repo-level Debugging 是唯一主线，Mini-Repo-Debug 是核心数据，Verifier Reward 是 RL 信号，SFT → Knowledge Distillation → GRPO 是训练路线。

v0.9 不扩新场景，而是补实可执行性：

1. multi-step tool-use rollout 如何真正运行；
2. trajectory 如何转换成 SFT / 蒸馏 / GRPO 数据；
3. hardcode / unrelated edit / grounding / invalid action 如何程序化检测；
4. eval 如何保证不污染原始 repo；
5. 训练预算如何按 1-2 张 3090 可复现；
6. 面试时如何解释“已实现”和“规划中”的边界。

一句话：**从“设计上可行”升级为“执行协议清楚、reward 可计算、eval 可复现、训练数据可构造”。**

---

## 1. 项目一句话

**CodeGuide-Agent v0.9 是一个以可验证执行反馈驱动的 repo-level code repair agentic RL 系统。它将 Mini-Repo-Debug 任务建模为 multi-step tool-use trajectory，通过 isolated repo environment、structured action/observation、programmatic verifier reward 和 trajectory logging，支撑后续 SFT、知识蒸馏与小规模 GRPO 优化。**

---

## 2. Agent Execution Contract

一个 episode 必须遵守固定协议：

```text
Step 0: Load Task
- issue.md
- repo path
- public test command
- optional hidden test command
- metadata: gold files/functions only for evaluation, not for agent context

Step 1: Create Isolated Workspace
- copy original mini repo to temp workspace
- all edits/tests happen inside temp workspace
- original dataset repo must remain unchanged

Step 2: Initialize State
- repo tree summary
- issue text
- empty trajectory log
- empty opened_files / searched_queries / edited_files / tests_run

Step 3: Policy Emits Structured Action
- action_name
- action_input
- optional thought / rationale

Step 4: Tool Execution
- tool validates input
- tool runs inside temp workspace
- tool returns structured observation

Step 5: State & Trajectory Update
- append action/observation to JSONL trajectory
- update debug memory summary

Step 6: Verification / Reward Checkpoint
- run tests when requested or at terminal state
- compute diff
- compute reward components
- run hacking checks

Step 7: Termination
- public/hidden tests pass
- agent emits stop
- max steps reached
- repeated invalid actions
- unrecoverable tool failure
```

### Action Schema

```json
{
  "thought": "Issue mentions YAML config support. Search for config loading code.",
  "action_name": "search_repo",
  "action_input": {
    "query": "load_config yaml config",
    "path": ".",
    "file_glob": "*.py"
  }
}
```

### Observation Schema

```json
{
  "tool_name": "search_repo",
  "status": "success",
  "observation": {
    "matches": [
      {
        "file": "src/config_loader.py",
        "line": 12,
        "text": "def load_config(path):"
      }
    ]
  },
  "error": null
}
```

核心原则：

```text
The model proposes actions.
The environment executes tools.
The verifier computes reward.
The dataset repo is never mutated.
```

---

## 3. Training Framework & Rollout Implementation

### 3.1 为什么标准 single-turn GRPO 不够？

普通 TRL-style GRPO/PPO 通常假设：

```text
prompt → model response → scalar reward
```

但 CodeGuide-Agent 是：

```text
prompt/state
→ tool action
→ observation
→ new state
→ next action
→ patch
→ test feedback
→ terminal reward
```

因此，训练对象不是单轮 response，而是完整 action-observation trajectory。

### 3.2 分层架构

```text
Policy Model
  ↓ generates structured action
Rollout Collector
  ↓ manages loop/state/termination
Tool Environment
  ↓ executes repo_tree/search/read/edit/test/git_diff/rollback
Verifier Reward Engine
  ↓ computes outcome/process/safety reward
Trajectory Store
  ↓ builds SFT / distillation / GRPO data
```

### 3.3 分阶段路线

| Phase | 目标 | 说明 |
|---|---|---|
| Phase 1 | Deterministic tools + logger | Mini-Repo-Debug、tools、trajectory、reward v1 |
| Phase 1.5 | Eval/reward hardening | isolated eval、pytest preflight、hacking checks |
| Phase 2 | Successful trajectory SFT | 学会工具调用格式和基本修复流程 |
| Phase 3 | Knowledge Distillation | 学 root cause、evidence、patch rationale |
| Phase 4 | Custom Rollout Collector | 同一任务采样多条 multi-step trajectories |
| Phase 5 | Trajectory-level GRPO PoC | 用 verifier reward 优化工具策略和修复路径 |

---

## 4. Rollout Implementation Options

### Option A：Self-built Rollout Collector（推荐）

优点：
- 工具调用、状态更新、reward、日志完全可控；
- 最适合当前个人项目；
- 面试时能讲清楚每一步；
- 不受单轮 trainer 限制。

缺点：
- 需要自己维护 rollout loop 和 training data builder；
- 后期接 GRPO trainer 时需要适配。

### Option B：verl / OpenRLHF 风格 Agentic RL 集成

优点：
- 适合规模化；
- 更接近工业训练体系。

缺点：
- 工程复杂；
- 多步 tool-use environment 适配成本高；
- 对 6 张非独占 3090 不友好。

### Option C：TRL-style 简化实验

用途：
- 只做 offline simplified GRPO / DPO ablation；
- 不作为主 rollout 框架。

限制：
- 无法自然表达 tool action → observation → next action 的真实环境交互。

v0.9 结论：

> 当前实现先做自研 rollout collector interface，训练框架只预留接口，不直接上完整 GRPO。

---

## 5. Trajectory-to-Training-Data Conversion

### 5.1 Successful Trajectories → SFT

保留：
- issue context
- repo summary
- action sequence
- tool observations
- final patch
- test result

示例：

```json
{
  "messages": [
    {"role": "system", "content": "You are CodeGuide-Agent, a repo-level code repair agent."},
    {"role": "user", "content": "<issue>...</issue><repo_tree>...</repo_tree>"},
    {"role": "assistant", "content": "<action>{...}</action>"},
    {"role": "tool", "content": "<observation>{...}</observation>"},
    {"role": "assistant", "content": "<final_patch>...</final_patch>"}
  ],
  "metadata": {
    "task_id": "task_001",
    "final_status": "success",
    "source": "successful_trajectory"
  }
}
```

### 5.2 Distillation Data

强模型生成压缩推理字段：

```json
{
  "task_id": "task_001",
  "root_cause": "load_config always parses config files with json.loads.",
  "evidence": [
    {
      "file": "src/config_loader.py",
      "lines": [12, 18],
      "symbol": "load_config",
      "source": "opened_file"
    }
  ],
  "patch_rationale": "Branch on .yaml/.yml extension and use yaml.safe_load; keep JSON behavior unchanged."
}
```

### 5.3 Failed Trajectories → Negative / Diagnostic Data

失败轨迹保留用于：
- reward hacking analysis；
- GRPO rollout groups；
- hard case curriculum；
- tool policy diagnosis；
- future DPO rejected candidates for QA-like preferences。

### 5.4 Same Task Multi-Rollout → GRPO Group

```json
{
  "task_id": "task_001",
  "rollouts": [
    {"trajectory_id": "traj_a", "reward": 0.92, "status": "success"},
    {"trajectory_id": "traj_b", "reward": 0.35, "status": "partial"},
    {"trajectory_id": "traj_c", "reward": -0.20, "status": "regression"},
    {"trajectory_id": "traj_d", "reward": 0.05, "status": "fail"}
  ]
}
```

Group-relative advantage：

```text
adv_i = (r_i - mean(r_group)) / (std(r_group) + 1e-6)
```

如果 group 内 reward 全相等，则跳过该 group 或使用 moving baseline。

---

## 6. Executable Reward Rules

### 6.1 总公式

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
- 0.10 * P_invalid_action
- 0.05 * P_duplicate_tool
- 0.05 * P_timeout
```

### 6.2 Outcome Reward

```text
public tests pass: +0.4
hidden tests pass: +0.6
partial pass: pass_ratio * 0.5
```

### 6.3 Process Reward

```text
gold_file_hit@3: +0.25
gold_function_hit@3: +0.25
failure_count_decreases_after_patch: +0.25
correct_stop_after_pass: +0.15
rollback_after_regression: +0.10
```

### 6.4 Patch Safety Reward

```text
changed_files <= 2: +0.30
changed_lines <= 30: +0.30
no_test_files_modified: +0.20
no_unrelated_files_modified: +0.20
```

### 6.5 Grounding Reward

尽量程序化，不依赖 LLM judge：

```text
cited file exists
line range exists
symbol exists if provided
cited file was opened OR evidence comes from test logs
```

### 6.6 Efficiency Reward

```text
tool_calls <= max_tool_steps
duplicate_search <= threshold
opened_irrelevant_files <= threshold
episode stops after success
```

---

## 7. Programmatic Reward-Hacking Checks

### 7.1 Test Deletion / Modification

Flag if patch modifies：

```text
tests/
tests_hidden/
pytest config that disables tests
```

强惩罚：

```text
P_test_deletion = 1.0
```

### 7.2 Hardcode Detection

Heuristic triggers：

```text
1. newly added string literal matches public expected output;
2. newly added numeric literal matches public expected number;
3. source code references test file name / fixture name;
4. branch condition contains public sample value;
5. code references tests/ or tests_hidden/.
```

Output：

```json
{
  "hardcode_flag": true,
  "reasons": [
    "new literal matches public expected output"
  ]
}
```

### 7.3 Unrelated Edit Detection

Allowed files：

```text
allowed_files = gold_files ∪ top_k_suspicious_files ∪ explicitly opened relevant files
```

Flag if：

```text
changed_file not in allowed_files
and changed_file not clearly generated/cache file
and changed_file not allowed config update
```

### 7.4 Patch Minimality

Programmatic features：

```text
changed_files_count
changed_lines_count
changed_functions_count if available
test_files_modified
large_delete_ratio
```

### 7.5 Invalid Action Penalty

Track：

```text
invalid_json_count
unknown_tool_count
missing_arg_count
tool_timeout_count
duplicate_tool_call_count
```

Penalty：

```text
P_invalid_action = min(1.0, 0.1 * invalid_action_count)
```

---

## 8. Grounding Citation Schema

Agent root-cause/evidence outputs should use：

```json
{
  "claim": "YAML config is parsed as JSON.",
  "evidence": [
    {
      "file": "src/config_loader.py",
      "lines": [12, 18],
      "symbol": "load_config",
      "source": "opened_file"
    }
  ]
}
```

Allowed source types：

```text
opened_file
test_log
repo_tree
search_result
```

Verifier checks：
- file exists
- line range valid
- symbol present if provided
- source was actually observed in trajectory

Invalid citation cases：
- nonexistent file
- invalid line range
- file never opened and not in test logs/search results
- symbol not found

---

## 9. Invalid Action Handling

### 9.1 Invalid JSON

```text
record invalid_json_count += 1
allow one retry if retry budget remains
otherwise append failed observation
```

### 9.2 Unknown Tool

```text
record unknown_tool_count += 1
return observation: status=failed, error=unknown_tool
```

### 9.3 Missing Required Args

```text
record missing_arg_count += 1
return structured error with required schema
```

### 9.4 Tool Timeout

```text
record tool_timeout_count += 1
terminate tool call
allow agent to choose next action
```

### 9.5 Duplicate Useless Calls

Definition：

```text
same tool + same args + no new information
```

Penalty：

```text
duplicate_tool_call_count += 1
```

---

## 10. Evaluation Design

### 10.1 Isolated Evaluation

All eval must run in temp workspace：

```text
copy task repo → temp workspace
apply patch inside temp
run tests inside temp
compute diff/reward
delete temp unless keep-temp
verify original repo unchanged
```

### 10.2 Public vs Hidden Tests

```text
public tests:
agent may run during episode

hidden tests:
only evaluator runs at terminal state
not exposed to agent
```

### 10.3 Required Metrics

```text
repair_success
public_pass_rate
hidden_pass_rate
gold_file_hit@3
gold_function_hit@3
avg_tool_calls
avg_changed_files
avg_changed_lines
test_file_modified_rate
hardcode_flag_rate
unrelated_edit_rate
invalid_action_rate
timeout_rate
regression_rate
original_repo_unchanged_rate
```

---

## 11. Compute & Time Budget

### 11.1 Default Reproducible Setup

Assume：

```text
1-2 × RTX 3090
non-exclusive environment
24GB GPU memory
```

6 × 3090 is upper bound, not default assumption.

### 11.2 Rough Runtime Estimates

| Stage | Model | Scale | Estimated Time |
|---|---|---:|---:|
| SFT QLoRA | Qwen2.5-Coder-3B | 300-800 trajectories | 1-3h |
| SFT QLoRA | Qwen2.5-Coder-7B | 300-800 trajectories | 2-6h |
| Distillation Generation | API / strong model | 300-800 samples | API-bound |
| Rollout Collection | 3B/7B/API | 50-100 tasks × 4-8 rollouts | 1-6h |
| GRPO PoC | 3B | 50-100 tasks | 3-10h |
| GRPO PoC | 7B QLoRA | 50-100 tasks | 6-20h, unstable |

Practical rule：

```text
3B is for fast GRPO proof-of-concept.
7B QLoRA is for SFT/distillation main experiment.
Multi-card GRPO is optional, not assumed.
```

---

## 12. What Is Implemented vs Planned

### Implemented / Phase 1 + 1.5

```text
Mini-Repo-Debug schema
5 handcrafted tasks
tool layer
trajectory logger
reward v1
isolated eval
pytest preflight
hardcode/unrelated edit checks
citation verifier skeleton
invalid-action penalty fields
```

### Planned / Phase 2

```text
rollout collector skeleton
successful trajectory SFT builder
distillation data builder
larger Mini-Repo-Debug dataset
```

### Planned / Phase 3+

```text
small-scale GRPO
reward normalization
policy collapse monitoring
Code QA + RAG secondary line
Vulnerability Lite evaluation
```

### Not in Current Scope

```text
IDE completion
VLM
generic multi-agent
large-scale SWE-bench training
large-scale GRPO
```

---

## 13. Interview Defense

### Q1：为什么不做五个代码场景？

字节 JD 里的 IDE 补全、QA、Agent、修复、漏洞检测是应用方向，不是要求一个实习项目全部做深。Auto Repair 有最可靠的 verifier reward：测试是否通过、是否回归、patch 是否最小、是否 hardcode，所以它最适合承载 SFT、蒸馏和 Agentic RL。

### Q2：为什么 SFT / 蒸馏后还要 GRPO？

SFT 学成功轨迹的模仿，蒸馏学强模型的中间分析，但它们不能直接优化什么时候 search、read、patch、run_test、stop，也不能直接惩罚多余工具调用和 regression。这些是环境反馈和工具策略问题，更适合 trajectory-level GRPO。

### Q3：为什么不用 DPO 做 repair？

Repair 的核心信号是可验证的：tests pass、no regression、patch minimality、hidden pass。这些不需要包装成主观偏好。DPO 更适合 Code QA 中的 grounded answer vs hallucinated answer。

### Q4：怎么防 reward hacking？

显式检测删测试、改 tests_hidden、hardcode public case、大范围无关修改、只过 public 不过 hidden、不跑测试就声称成功。checkpoint 选择不只看训练 reward，还看 hidden pass、regression rate、hardcode rate、tool cost、changed lines。

### Q5：Mini-Repo-Debug 会不会太 synthetic？

Mini-Repo-Debug 是可控合成数据，不是 SWE-bench 替代品。它的作用是让 gold file/function、hidden tests、reward hacking checks 都可控，从而快速验证 agentic training pipeline。后续可接少量 SWE-bench Lite sanity tasks 做真实性验证。

### Q6：如何避免 issue 泄漏 gold file/function？

任务构造时要求 issue 不直接出现 gold file/function 名；metadata 只给 evaluator；agent context 不包含 metadata；gold files/functions 仅用于 reward。可以做 leakage audit：检查 issue 是否包含 exact gold file/function names。

### Q7：什么已经实现，什么只是规划？

已实现：dataset schema、5 tasks、tools、eval、reward v1、isolated eval、hacking checks。  
规划中：rollout collector、SFT builder、distillation builder、GRPO PoC。

---

## 14. Next Milestones

### Phase 2：Rollout Collector Skeleton

目标：

```text
policy backend → action → tool → observation → trajectory
```

支持：

```text
mock policy
gold policy
API policy placeholder
max steps
invalid action retry
trajectory output
```

### Phase 3：SFT Data Builder

目标：

```text
successful trajectory → chat-format SFT sample
```

### Phase 4：Distillation Data Builder

目标：

```text
strong model/API → root cause, evidence, patch rationale
```

### Phase 5：Small-scale GRPO PoC

目标：

```text
same task multiple rollouts
programmatic reward
group-relative advantage
3B/7B QLoRA proof-of-concept
```

---

## 15. 结论

v0.9 的核心判断：

> CodeGuide-Agent 的价值不在于堆更多代码场景，而在于把一个可验证代码修复场景做成“环境—工具—轨迹—reward—训练数据”的闭环。

最终项目定位：

```text
CodeGuide-Agent:
Executable Verifier-Driven Code Repair Agentic RL System
```

最小可实现路线：

```text
Phase 1/1.5:
dataset + tools + isolated eval + reward hardening

Phase 2:
rollout collector

Phase 3:
SFT / distillation

Phase 4:
small-scale GRPO
```
