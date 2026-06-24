# CodeGuide-Agent：Context Management / Memory / RAG 模块调研论证

## 0. 结论先行

当前 CodeGuide-Agent 已完成 `Mini-Repo-Debug v1` 的 100-task 里程碑，后续不建议继续单纯堆任务。下一步更有价值的是做三件事：

1. **新增 Context Management 模块**：把当前 agent 的“上下文窗口”从简单拼 prompt，升级为可预算、可压缩、可持久化、可追溯的 `Context Pack`。
2. **新增 RAG 检索模块**：从现在的 `search_repo` 关键词/正则检索，升级为“代码语义检索 + 历史轨迹检索 + 外部 API 文档检索”的三层 RAG。
3. **引入真实 SWE 数据集做外部对齐**：短期优先用 `SWE-bench Lite / Verified` 做 eval-style 适配；中期参考 `SWE-smith` 的自动任务生成；长期再考虑 `Scale-SWE / DeepSWE / R2E-Gym` 这类大规模训练路线。

一句话：**现在项目已经有 verifier-driven dataset 雏形，下一步应该从“数据集工程”进入“上下文工程 + 检索增强 + 真实 SWE 对齐”。**

---

## 1. 关于 Claude Code 源码：能学什么，不能做什么

用户给的参考仓库是：

```text
https://github.com/yasasbanukaofficial/claude-code
```

这个仓库自称是 Claude Code 源码镜像，并且 README 明确说明其来源与 sourcemap 泄露有关，也声明原始代码属于 Anthropic。基于这个事实，建议：

- **可以参考架构思想**：memory、context compaction、tool loop、subagent、session storage、rule loading。
- **不建议复制代码实现**：不要直接 vendor、粘贴、改写其具体源码；这会带来版权和合规风险。
- **更可靠的实现依据**应该来自官方 Claude Code 文档、Anthropic context engineering 文章、公开论文和我们自己项目的需求。

下面的方案只抽象架构模式，不复用其源码。

---

## 2. Claude Code / 现代 coding agent 的上下文管理模式

### 2.1 Claude Code 的公开 memory 机制

官方 Claude Code 文档说明，每个 Claude Code session 都从 fresh context window 开始，跨 session 的知识主要靠两类机制：

1. `CLAUDE.md`：用户写的项目级 / 用户级 / 组织级持久指令。
2. Auto memory：Claude 根据用户纠正、偏好、调试经验自动沉淀的 notes。

这说明 Claude Code 的记忆不是“把所有历史都塞进 prompt”，而是：**启动时加载短规则，运行时按需检索/读取，长期经验单独持久化**。

对 CodeGuide-Agent 的启发：

```text
不要让 agent 每次看到所有历史轨迹、所有文件、所有 README。
应该让 agent 先拿一个轻量 Context Pack，再通过工具按需拿 code/doc/history。
```

### 2.2 CLAUDE.md / AGENTS.md 的加载方式

Claude Code 官方文档还说明，`CLAUDE.md` 可以在多个层级存在：

```text
organization / user / project / local / subdirectory
```

并且越靠近当前 working directory 的规则越后加载，Claude 读文件进入子目录时也可以按需加载子目录规则。这对 CodeGuide-Agent 很关键，因为 repo-level debugging 经常有：

```text
根目录通用规范
tests/ 下的测试规范
src/module_x 下的模块约束
某个任务自己的 issue 约束
```

所以 CodeGuide-Agent 不应只有一个 `AGENTS.md`，而应该支持**分层 context rules**：

```text
AGENTS.md
.codeguide/rules/*.md
data/mini_repo_debug/repos/task_xxx/AGENTS.md
repo 子目录局部规则
```

### 2.3 just-in-time context 比预先塞满上下文更适合代码库

Anthropic 的 context engineering 文章强调，agent 可以维护 lightweight identifiers，比如 file paths、stored queries、web links，然后在 runtime 通过工具动态加载上下文，而不是预处理后一次性加载所有内容。

这正好对应 CodeGuide-Agent 的下一步：

```text
当前：issue + repo_tree + search_repo + read_file
目标：issue + compact repo map + semantic retrieval + targeted read_file + history example retrieval
```

也就是把上下文管理从“静态 prompt assembly”升级为“动态上下文预算器”。

---

## 3. CodeGuide-Agent 应新增的 Context Management 模块

### 3.1 模块目标

新增模块：

```text
codeguide_agent/context/
```

核心职责：

1. 管理当前任务的上下文预算。
2. 决定哪些内容进 prompt，哪些内容只保留引用。
3. 压缩历史 tool observations。
4. 存储和检索跨任务经验。
5. 给 agent 每一步生成一个结构化 `Context Pack`。

### 3.2 建议目录结构

```text
codeguide_agent/context/
  __init__.py
  schemas.py              # ContextItem / ContextPack / MemoryRecord schema
  manager.py              # ContextManager 主入口
  budget.py               # token / char budget 管理
  compaction.py           # tool trace / file snippet / plan summary 压缩
  memory_store.py         # session/project/experience memory store
  selectors.py            # context item scoring + top-k selection
  pack_builder.py         # 构造最终 prompt/context pack
  serializers.py          # jsonl / markdown / compact text 输出
```

### 3.3 ContextItem schema

建议先用简单 JSON schema，不要一开始引入复杂数据库：

```json
{
  "id": "ctx_...",
  "task_id": "task_076",
  "kind": "issue|repo_map|file_snippet|test_result|history_case|doc_snippet|memory_note",
  "source": "issue.md|read_file|semantic_search|history_rag|docs_rag|memory",
  "content": "...",
  "path": "optional/file.py",
  "score": 0.82,
  "tokens_est": 420,
  "metadata": {
    "created_at": "...",
    "confidence": "high",
    "leakage_safe": true
  }
}
```

### 3.4 ContextPack schema

每轮 agent 调用前构造：

```json
{
  "task_id": "task_076",
  "budget": {
    "max_tokens": 12000,
    "used_tokens_est": 7800
  },
  "sections": {
    "system_rules": [],
    "project_rules": [],
    "issue": [],
    "repo_map": [],
    "active_plan": [],
    "retrieved_code": [],
    "retrieved_history": [],
    "retrieved_docs": [],
    "recent_tool_summary": []
  },
  "dropped": [
    {
      "id": "ctx_x",
      "reason": "low_score_or_budget"
    }
  ]
}
```

### 3.5 上下文选择策略

先不要做复杂 RL，使用 deterministic scoring：

```text
score =
  0.35 * semantic_relevance_to_issue
+ 0.20 * lexical_match
+ 0.15 * recency
+ 0.15 * structural_importance
+ 0.10 * tool_feedback_importance
+ 0.05 * historical_success_prior
```

特殊 hard rules：

```text
必须保留：
- issue.md
- public test command
- active plan
- last failed test summary
- files already edited
- gold/reference 信息只允许在 training/export 阶段使用，不允许在 inference/agent repair 阶段进入 prompt
```

---

## 4. Context Compaction 设计

### 4.1 为什么需要 compaction

随着 agent 工具调用增多，最大问题不是“找不到信息”，而是：

```text
工具输出太多
重复读文件
测试日志太长
历史轨迹塞爆上下文
模型忘记当前计划
```

所以要做四类 compaction。

### 4.2 Tool Observation Compaction

将原始 tool trace：

```text
run_test full stdout/stderr
read_file full content
search_repo full results
git diff full diff
```

压缩成：

```text
- command
- exit code
- top failure
- changed files
- relevant stack frame
- next action hint
```

保留原始日志到磁盘：

```text
.codeguide/sessions/{session_id}/raw_tool_logs.jsonl
```

prompt 里只放摘要。

### 4.3 File Context Compaction

文件不直接全量塞入 prompt，而是按结构切片：

```text
imports
class/function signatures
related function body
nearby callsites
tests that mention same symbol
```

对 Python 可以先用 AST；其他语言先 fallback 到 tree-sitter 或 regex chunk。

### 4.4 Trajectory Compaction

历史成功修复轨迹不直接塞全轨迹，而是转成：

```text
Issue pattern:
Failure signal:
Localization clue:
Patch strategy:
Files changed:
Why rejected attempts failed:
Final minimal patch summary:
```

### 4.5 Memory Compaction

项目长期记忆分三层：

```text
.codeguide/memory/project.md       # 项目稳定规则
.codeguide/memory/debug_cases.jsonl # 成功/失败经验
.codeguide/memory/api_docs/         # 外部文档缓存摘要
```

每次任务结束自动写入一条 `ExperienceRecord`。

---

## 5. RAG 模块：为什么值得做

当前 `search_repo` 主要依赖关键词 / 正则。当代码库变大时，会遇到三个问题：

1. **Issue 不知道函数名**：例如“退款超时逻辑错误”，但代码里叫 `settlement_grace_period`。
2. **跨模块隐式依赖**：bug 在 service 层表现，但根因在 config / cache / validator。
3. **历史经验无法复用**：已经修过相似 bug，但 agent 不知道以前怎么定位和修。

因此建议新增：

```text
codeguide_agent/rag/
```

并提供三类检索：

```text
1. Code RAG：语义级代码检索
2. History RAG：历史修复轨迹检索
3. Docs RAG：外部 API 文档检索
```

---

## 6. Code RAG 设计

### 6.1 目标

让 agent 可以用自然语言检索代码：

```text
“寻找处理用户超时退款的逻辑”
“哪里在合并 CLI 参数和默认 config”
“哪个模块负责 reset initialized state”
```

而不是必须知道：

```text
grep -R "refund_timeout"
grep -R "merge_config"
grep -R "reset_initialized"
```

### 6.2 索引内容

对每个 repo/task 构建：

```text
file path
module docstring
imports
class/function signature
function body chunk
callers/callees
tests mentioning symbol
git metadata if available
```

### 6.3 存储建议

本地轻量方案：

```text
.codeguide/index/code_chunks.jsonl
.codeguide/index/bm25.sqlite
.codeguide/index/faiss.index 或 lancedb/
```

先做不依赖大型服务的实现：

```text
BM25 / ripgrep lexical
+ sentence-transformers embedding
+ metadata filter
+ optional LLM rerank
```

### 6.4 检索流程

```text
query = issue + current failure summary + active hypothesis

stage 1: lexical retrieval
stage 2: semantic retrieval
stage 3: path/type filters
stage 4: rerank
stage 5: return compact snippets + file references
```

返回结构：

```json
{
  "query": "where is timeout refund handled",
  "results": [
    {
      "path": "src/refund/service.py",
      "span": "L40-L95",
      "kind": "function",
      "score": 0.87,
      "why": "mentions timeout window and refund state transition",
      "snippet": "..."
    }
  ]
}
```

### 6.5 新工具接口

新增 tools：

```text
semantic_search_repo(query, top_k=8, filters=None)
read_semantic_result(result_id)
explain_retrieval(result_id)
```

保留现有 `search_repo`，不要替换：

```text
search_repo = 精确定位
semantic_search_repo = 模糊意图定位
```

---

## 7. History RAG：最值得做的差异化点

这是最适合 CodeGuide-Agent 的 RAG 方向。

### 7.1 为什么历史轨迹 RAG 最有价值

你的项目已经有：

```text
100 tasks
SFT records
preference pairs
hard preference
rollouts
gold patches
```

这意味着你已经有很多“修复经验”。不要只把它们当训练数据，也应该把它们变成 inference-time memory。

### 7.2 ExperienceRecord schema

每个成功/失败修复都转成：

```json
{
  "experience_id": "task_076_gold_reference",
  "task_id": "task_076",
  "issue_summary": "...",
  "bug_pattern": "missing helper function / hidden import failure",
  "failure_signal": "public passes but hidden import fails",
  "repo_context": ["task_076_lib/validator.py"],
  "patch_summary": "add is_even helper",
  "gold_patch": "diff --git ...",
  "negative_attempts": [
    {
      "policy": "noop",
      "reason": "public passed but hidden failed",
      "reward_summary": {"public_pass": true, "hidden_pass": false}
    }
  ],
  "embedding_text": "issue + failure + patch summary + reason labels",
  "tags": ["hard_pair", "hidden_import_or_syntax", "validator"]
}
```

### 7.3 检索方式

新任务开始时：

```text
query = issue.md + public failure + repo tree summary
retrieve top_k historical cases
```

返回给 agent 的不是完整 patch，而是 few-shot 经验摘要：

```text
Similar past case:
- Symptom: public tests passed but hidden failed due missing helper export
- Localization: validator.py contained only is_positive; hidden imported is_even
- Strategy: inspect hidden-like import expectations from issue wording; add minimal helper
- Avoid: no-op passed public but failed hidden
```

### 7.4 防止泄漏

History RAG 不能在 evaluation/inference 时暴露当前任务 gold patch。规则：

```text
允许：
- 过去任务的 issue pattern
- 过去任务的 patch strategy summary
- 过去任务的 changed file types
- 过去失败尝试的 reason label

禁止：
- 当前 task 的 gold.patch
- 当前 hidden tests
- 当前 hidden output
- 与当前任务同源的 oracle metadata
```

### 7.5 与训练数据的关系

History RAG 也可以进入训练：

```text
SFT 输入 = issue + retrieved_history_summaries + tool context
SFT 输出 = patch
```

这样未来模型会学会“使用检索上下文修复”。

---

## 8. API Docs RAG

### 8.1 使用场景

当 bug 涉及外部库：

```text
requests timeout
pandas date parse
click argparse behavior
fastapi response model
sqlalchemy session lifecycle
```

纯靠模型记忆容易幻觉，所以需要 docs RAG。

### 8.2 实现方式

先做离线/缓存优先：

```text
.codeguide/docs_cache/{package}/{version}/chunks.jsonl
```

工具：

```text
fetch_api_docs(package, version, topic)
search_api_docs(query, package=None, version=None)
```

### 8.3 安全边界

必须加 allowlist：

```text
python stdlib
pytest
requests
click
pydantic
fastapi
sqlalchemy
pandas
```

不要让 agent 任意联网抓网页。动态拉取可以作为后续功能，第一版只做手动导入 / allowlist fetch。

---

## 9. RAG 与 Context Manager 的整合

最终 agent loop 应该从：

```text
issue -> repo_tree -> search_repo -> read_file -> edit -> test
```

升级成：

```text
issue
-> context_manager.build_initial_pack()
-> semantic_search_repo()
-> retrieve_history()
-> maybe search_api_docs()
-> read selected files
-> edit
-> run tests
-> compact observations
-> update memory
```

每一步都由 `ContextManager` 控制预算：

```text
保留高价值上下文
压缩长日志
丢弃低相关 snippets
只保留引用，不塞全文
```

---

## 10. 数据集调研与适配建议

### 10.1 SWE-bench Lite / Verified

适合做 **外部评测适配**。

优点：

```text
真实 GitHub issue
标准化 benchmark
SWE-bench Lite 成本低
Verified 更可信
```

缺点：

```text
环境构建复杂
完整 agent loop 成本高
不适合作为第一阶段训练主数据
```

建议：

```text
P0：先做 SWE-bench Lite 10-instance adapter
P1：能跑 repo setup / issue / patch / eval
P2：只做 evaluation，不直接混入训练
```

### 10.2 SWE-smith

适合做 **任务扩展生成器参考**。

SWE-smith 的核心价值是把任意 Python repo 转成 SWE-gym，并自动生成 file localization / program repair / SWE-bench 风格任务。公开资料显示其目标就是训练 SWE agents，且可以从代码库生成大量任务。

对 CodeGuide-Agent 的启发：

```text
你现在半自动构造了 100 个 mini tasks。
下一步可以借鉴 SWE-smith，把任务生成器泛化到真实 Python repo。
```

建议：

```text
优先级最高的数据生成参考。
不是马上导入其 50k 数据，而是复刻它的“repo -> task generator -> verifier”的思路。
```

### 10.3 Scale-SWE

Scale-SWE 更像长期目标。公开论文描述它用 sandboxed multi-agent workflow，从大量 PR 构造 100k verified SWE instances，并蒸馏 71,498 条高质量轨迹用于训练。

优点：

```text
规模大
更贴近真实 PR
强调 environment setup / unit test generation / problem synthesis
```

缺点：

```text
工程复杂度远高于当前项目
对算力和基础设施要求高
不适合立刻接入
```

建议：

```text
作为 roadmap 参考，不作为当前阶段依赖。
```

### 10.4 DeepSWE / R2E-Gym

DeepSWE 代表“纯 RL 训练 coding agent”的路线。公开资料称其基于 Qwen3-32B，用约 4,500 个 R2E-Gym real-world SWE tasks，在 64 H100 上训练数天。

对当前项目的启发：

```text
经验驱动 / execution reward 很重要
但当前资源和数据规模不适合直接走 DeepSWE 式 RL
```

建议：

```text
短期不要做 full RL。
可以先做：
- smoke SFT
- DPO smoke
- reward/replay evaluator
- trajectory RAG
```

### 10.5 SWE-World / SWE-Bench-CL

SWE-World 适合思考“无 Docker / surrogate execution”路线；SWE-Bench-CL 适合思考“continual learning + semantic memory”。其中 SWE-Bench-CL 明确把 FAISS-backed semantic memory 用于 coding-agent continual learning，这和我们要做的 History RAG 高度一致。

建议：

```text
History RAG 设计可以参考 SWE-Bench-CL 的 continual-memory framing。
```

---

## 11. 推荐技术路线

### 阶段 A：收口 100-task v1

目标：

```text
commit + tag
make test green
audit green
scale report frozen
```

产物：

```text
mini-repo-debug-v1-100tasks tag
docs/PROJECT_STATUS_V1.md
```

### 阶段 B：Context Management v0

新增：

```text
codeguide_agent/context/
```

最小功能：

```text
ContextItem
ContextPack
tool observation compaction
session memory jsonl
project memory markdown
```

验证：

```text
unit tests
context pack snapshot tests
no hidden leakage tests
```

### 阶段 C：Code RAG v0

新增：

```text
codeguide_agent/rag/code_index.py
codeguide_agent/rag/retriever.py
tools/semantic_search_repo
```

先做：

```text
BM25 + embeddings
Python AST chunks
top-k snippets
```

不要一开始做复杂 graph RAG。

### 阶段 D：History RAG v0

新增：

```text
experience extraction from train_package + rollouts
history index
retrieve_similar_fixes
```

重点评估：

```text
hard-pair tasks localization 是否更快
tool steps 是否减少
public-pass-hidden-fail 是否更容易修
```

### 阶段 E：SWE-bench Lite Adapter

目标：

```text
导入 10 个 SWE-bench Lite / Verified instances
只跑 evaluation adapter
不混入训练
```

验证：

```text
repo setup
issue ingestion
patch output
test command wrapper
result schema
```

---

## 12. 具体文件级改造建议

### 12.1 Context Management

新增：

```text
codeguide_agent/context/schemas.py
codeguide_agent/context/manager.py
codeguide_agent/context/compaction.py
codeguide_agent/context/memory_store.py
codeguide_agent/context/pack_builder.py
tests/test_context_manager.py
```

### 12.2 RAG

新增：

```text
codeguide_agent/rag/chunking.py
codeguide_agent/rag/code_index.py
codeguide_agent/rag/history_index.py
codeguide_agent/rag/docs_index.py
codeguide_agent/rag/retriever.py
codeguide_agent/tools/semantic_search_repo.py
codeguide_agent/tools/retrieve_history.py
tests/test_rag_code_index.py
tests/test_rag_history.py
```

### 12.3 数据与评估

新增：

```text
scripts/build_code_rag_index.py
scripts/build_history_rag_index.py
scripts/eval_rag_localization.py
docs/RAG_CONTEXT_MANAGEMENT_PLAN.md
```

---

## 13. MVP 实施顺序

### 第 1 步：Context Pack

不要先做向量库，先把上下文对象化：

```text
issue
repo map
retrieved files
test output summary
history snippets
docs snippets
```

### 第 2 步：History RAG

因为你已经有 100 tasks，最容易产生收益：

```text
train_package + rollouts -> experience records -> top-k retrieval
```

### 第 3 步：Code RAG

用 task repo 做小规模验证：

```text
query: "where is CLI argument propagation handled"
expect: target file top-3
```

### 第 4 步：API Docs RAG

只做 allowlist + cache，不做开放网络浏览。

### 第 5 步：SWE-bench Lite adapter

确认外部真实任务兼容性。

---

## 14. 给 Codex 的下一步大粒度 Prompt

```text
You are working in /Users/yjx/Code/CodeGuide-Agent.

Goal: implement Context Management v0 and History RAG v0. Do not train. Do not call external APIs. Do not use llm policy.

Current project status:
- Mini-Repo-Debug v1 has 100 active tasks.
- SFT=100, preference=169, hard preference=64.
- make test, audit, scale-report are green.
- We want to improve agent context handling before GPU smoke training.

Tasks:
1. Add codeguide_agent/context/ with:
   - ContextItem / ContextPack schemas
   - ContextManager
   - budget-aware context selection
   - tool observation compaction
   - session memory jsonl store
2. Add codeguide_agent/rag/history_index.py:
   - build ExperienceRecord from train_package and rollouts
   - index issue summary, patch summary, failure signal, reason labels
   - retrieve top-k similar experiences by lexical + simple embedding fallback if available
3. Add tools:
   - retrieve_history(query, top_k)
   - build_context_pack(task_id, issue, retrieved_history, tool_summary)
4. Add scripts:
   - scripts/build_history_rag_index.py
   - scripts/eval_history_rag_retrieval.py
5. Add tests:
   - no hidden test leakage in ContextPack
   - history retrieval returns same-pattern tasks
   - compaction removes long raw logs but preserves failure signal
6. Add docs:
   - docs/RAG_CONTEXT_MANAGEMENT_PLAN.md

Validation:
- make test
- make audit
- make scale-report
- python -m compileall codeguide_agent

Do not start training.
Do not claim performance improvement.
```

---

## 15. 最终建议

当前最优路线不是马上训练，而是：

```text
1. 固化 100-task v1
2. 做 Context Management v0
3. 做 History RAG v0
4. 做 Code RAG v0
5. 接 SWE-bench Lite 10-instance eval adapter
6. 再做 GPU smoke SFT
```

原因：

```text
训练前，agent 的上下文和检索能力会直接决定数据质量、轨迹质量和真实 repo 泛化能力。
现在 100-task dataset 已经够做内部验证；下一步应该让 agent 更会找上下文，而不是继续盲目扩数据。
```

---

## References

- [S1] GitHub mirror README for `yasasbanukaofficial/claude-code`
- [S2] Official Claude Code memory documentation
- [S3] Anthropic engineering: effective context engineering for AI agents
- [S4] Claude API memory tool documentation
- [S5] SWE-bench / SWE-bench Lite / SWE-bench FAQ
- [S6] SWE-smith paper / repository
- [S7] Scale-SWE paper
- [S8] DeepSWE / Together AI technical blog
- [S9] SWE-Bench-CL continual-learning paper
