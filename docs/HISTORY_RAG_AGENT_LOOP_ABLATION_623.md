# History RAG Agent-Loop Ablation Report — P1.1

Generated: 2026-06-25
Dataset: Mini-Repo-Debug v1 (100 tasks, 200 experience records)

## 1. Ablation Design

Two conditions were compared across all 100 gold-reference tasks:

| Condition | History RAG | Snippets per task | Description |
|-----------|------------|-------------------|-------------|
| Baseline (disabled) | Off | 0 | No history context injected |
| History RAG (enabled) | On (quality mode) | 3 | retrieve_quality, capped at 3×600 chars |

Both conditions use the **same deterministic policies** (noop, heuristic, scripted) — no LLM involved. The ablation measures context-building safety, not policy performance.

## 2. Results

| Metric | Baseline | History RAG |
|--------|----------|-------------|
| Total tasks | 100 | 100 |
| Total snippets built | 0 | 300 |
| Avg snippets per task | 0.00 | 3.00 |
| Avg chars per snippet | — | 412 |
| Same-family warnings | 0 | 0 |
| Leakage safe | ✅ | ✅ |
| Leakage violations | 0 | 0 |

### Key Findings

1. **Disabled by default works** — When `HistoryRAGConfig.enabled=False`, zero snippets are built and no index is queried. All 100 tasks produce empty history context.

2. **Enabled builds safe snippets** — All 300 snippets (3×100) are within the 600-char cap (avg 412 chars). No `diff --git`, no `hidden_test`, no `oracle` content detected in any snippet.

3. **Same-family warning is quiet** — 0 warnings across 100 tasks. The 23 unique generator families provide sufficient diversity that no task's top-3 results are dominated by same-family records. The warning guard works when tested with artificially homogenous data.

4. **ContextPack integration verified** — Snippets are passed via `history_rag` parameter to `ContextManager.build_pack()`. Items receive `ItemRole.HISTORY_RAG` role with priority 4 (below ISSUE/TEST_SUMMARY/REPO_MAP, above TOOL_TRACE). This means history snippets are evicted before core context under budget pressure.

5. **Feature is fully self-contained** — No external APIs, no LLM dependency, no training data modification. The `HistoryRAGAgentLoop` class can be instantiated and injected anywhere in the rollout pipeline.

## 3. Leakage Safety Verification

| Check | Result |
|-------|--------|
| Full diff in retrieval_view | ❌ None (zero instances) |
| hidden_test / tests_hidden | ❌ None |
| oracle / evaluator_only | ❌ None |
| gold.patch in snippets | ❌ None |
| storage_view exposed | ❌ Not passed to agent |
| Same-task exclusion | ✅ task_id + patch_hash filtered |
| Char cap enforced | ✅ all ≤ 600 |
| Snippet count cap | ✅ all ≤ 3 |

## 4. Integration Architecture

```
HistoryRAGAgentLoop
  ├── HistoryRAGConfig (enabled, mode, max_snippets, max_chars_per_snippet)
  ├── build_history_context(task_id, issue_text, patch_hash) → HistoryRAGContext
  │     ├── retrieve_quality (task_id + patch_hash exclusion)
  │     ├── same-family warning guard
  │     ├── _build_safe_snippet (retrieval_view only, capped)
  │     └── _check_snippet_leakage
  ├── get_safety_report() → dict
  └── get_safety_log() → list[dict]
                │
                ▼
  ContextManager.build_pack(history_rag=ctx.to_context_pack_dicts())
                │
                ▼
  ContextPack (with HistoryRAG items at priority 4)
```

## 5. Readiness Verdict

### ✅ P1.1 PASSES — History RAG is ready to remain enabled for deterministic policy rollouts

**For non-LLM rollouts (noop, heuristic, scripted):**
- History RAG context building is safe and produces useful snippets
- Deterministic policies don't consume context, so there's no risk of leakage through policy actions
- The feature should remain **off by default** but can be enabled via config flag

**For future LLM rollouts (when allowed):**
- Before enabling History RAG with LLM policies, additionally verify:
  1. LLM prompt injection safety (snippets don't confuse the model)
  2. Token budget impact on overall prompt size
  3. Whether same-family warnings increase with LLM-generated queries
  4. Retrieval latency impact on rollout time

**Recommendation for P2:**
- Keep History RAG **off by default**
- Provide a `--enable-history-rag` flag in the rollout CLI
- Add same-family warning to rollout summary output
- When LLM policies are re-enabled, run a focused ablation with History RAG on/off

## 6. Validation Results

| Check | Result |
|-------|--------|
| make test | 163 passed (+16 new P1.1 tests) |
| make audit | PASS |
| make scale-report | SFT=100, preference=169, hard=64 (unchanged) |
| make p61-check | PASS |
| compileall | All compiled |
| build_history_rag_index | 200 records, 23 families, leakage_safe=True |
| eval_history_rag_retrieval | 7/7 passed |
| run_history_rag_ablation | overall_passed=True |
| run_agent_loop_ablation | overall_passed=True |

## 7. Blockers

- **None** — P1.1 passes all checks. The only limitation is that deterministic policies don't consume context, so the ablation measures context-building safety, not downstream policy impact. This is expected and intentional.
