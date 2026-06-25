# History RAG Readiness Report — P1.1 Gate

Generated: 2026-06-25
Dataset: Mini-Repo-Debug v1 (100 tasks, 200 experience records)

## 1. Ablation Summary

Three retrieval modes were evaluated across all 100 gold-reference tasks:

| Metric              | Quality      | Strict (4-dim) | Strict Full (5-dim) |
|---------------------|-------------|----------------|---------------------|
| family_hit@1        | 0.27        | 0.00           | 0.00                |
| family_hit@3        | 0.43        | 0.00           | 0.00                |
| family_hit@5        | 0.46        | 0.00           | 0.00                |
| file_hit@1          | 0.00        | 0.00           | 0.00                |
| file_hit@3          | 0.00        | 0.00           | 0.00                |
| file_hit@5          | 0.00        | 0.00           | 0.00                |
| avg_top5            | 5.0         | 5.0            | 0.0                 |
| coverage_empty_pct  | 0.0%        | 0.0%           | 100.0%              |
| leakage_safe        | True        | True           | True                |

### Mode Definitions

- **Quality**: exclude `task_id` + `patch_hash` — maximizes recall for related experiences
- **Strict (4-dim)**: exclude `task_id` + `generator_family` + `patch_hash` + `issue_pattern_hash` — prevents template-level leakage
- **Strict Full (5-dim)**: + `split` exclusion — requires multi-split data to be viable

## 2. Key Findings

### 2.1 Quality mode works
- 46% of queries retrieve a same-family experience within top-5
- 27% retrieve same-family at rank 1
- Zero leakage (no full diff, no hidden tests, no oracle in retrieval_view)
- Zero empty retrievals (coverage_empty=0%)

### 2.2 Strict mode is too aggressive for this dataset
- Same-family exclusion removes all semantically similar records
- 23 unique generator families for 100 tasks means families are small (~4 tasks/family avg)
- Strict mode still returns results (from different families) but family_hit=0
- File overlap is zero across all modes — each task has unique source files by design

### 2.3 Strict full mode requires multi-split data
- All 200 records share `split=train`
- Split exclusion eliminates 100% of candidates
- This mode is only viable with train/eval/test split separation

### 2.4 Retrieval quality characteristics
- Deterministic multi-field scoring (issue_summary 0.40, failure_signal 0.25, patch_summary 0.20, changed_files 0.10, strategy 0.05)
- Tie-breaking by experience_id ensures full determinism
- No external API dependencies — pure lexical overlap scoring
- Changed_files extraction from `localization.gold_files` is correct

## 3. Leakage Safety

All three modes pass leakage checks:
- No `diff --git` in retrieval_view
- No `hidden_test` or `tests_hidden` references
- No `oracle` or `evaluator_only` content
- `visibility.allow_full_diff_in_retrieval_prompt` = `false` enforced
- Storage layer (full diff) separated from retrieval layer (summaries only)

## 4. Readiness Verdict

### Recommendation: **CONDITIONAL PROCEED to P1.1 (agent loop connection)**

Quality mode is ready with the following conditions:

**Must-do before connecting:**
1. Use quality mode (`retrieve_quality`) for agent loop — exclude task_id + patch_hash only
2. Add a same-family warning: if top-3 all share same generator_family as current task, flag as potential template leakage
3. Cap retrieval at 3 snippets with hard token budget (max 600 chars each)
4. Monitor retrieval_view content in agent prompt — never include full diff
5. Do NOT use strict_full mode until multi-split data exists

**Acceptable risks:**
- Strict-mode recall is zero — this is a dataset characteristic, not a retrieval bug
- File-level hit is zero — tasks have unique files; file overlap isn't a useful signal here
- 54% of queries don't find a same-family match — retrieval is sparse but safe

**Blockers resolved:**
- P0 leakage safety: ✅ (no full diff/hidden/oracle)
- Deterministic scoring: ✅
- Coverage not silently empty: ✅ (quality mode returns 5.0 avg)
- Exclude filters tested: ✅ (task_id, family, patch_hash, pattern_hash, split all verified)
- Tests pass: ✅ (147 tests, including 12 new strict mode tests)

**Blockers remaining:**
- No train/eval split → strict_full mode unusable → split the dataset before P2
- Small families (avg 4.3 tasks) → strict mode recall will stay low until data grows

## 5. Validation Results

| Check | Result |
|-------|--------|
| make test | 147 passed |
| make audit | PASS |
| make scale-report | active=100, planned=0, SFT=100, preference=169, hard=64 |
| make p61-check | PASS |
| compileall | All compiled |
| build_history_rag_index | 200 records, 23 families, leakage_safe=True |
| eval_history_rag_retrieval | 7/7 passed |
| run_history_rag_ablation | overall_passed=True |

## 6. Next Steps (P1.1)

1. Add `retrieve_history` tool to agent loop using quality mode
2. Implement same-family warning guard
3. Add token budget enforcement in ContextPack for RAG snippets
4. Run end-to-end smoke test with 3-5 tasks
5. Measure tool-step-count impact vs baseline (no RAG)
