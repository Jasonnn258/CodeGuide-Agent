# P61-P100 Rollout Export 061-100

P61-P100 completes the Mini-Repo-Debug dataset by expanding from 60 to 100 active tasks using bounded local rollout policies without running real training, external APIs, or the `llm` policy.

## New Tasks

Added 40 active tasks across four difficulty blocks:

### Block 1: 061-070 (P50 bug types, medium)
- `task_061`: parsing edge case — version parser crashes on prerelease suffixes
- `task_062`: path handling — path resolver does not collapse `..` segments
- `task_063`: cache key — cache key ignores argument types (int vs float)
- `task_064`: optional/default args — query builder includes None values
- `task_065`: boundary condition — page count drops trailing items
- `task_066`: string normalization — whitespace collapser misses tab characters
- `task_067`: dict mutation — word freq counter destroys input list
- `task_068`: date boundary — days-in-month ignores leap years
- `task_069`: JSON config parsing — list accessor returns None for missing keys
- `task_070`: CLI argument propagation — mode flag parsed but hard-coded to upper

### Block 2: 071-080 (P55 bug types, medium)
- `task_071`: error handling — file reader silently swallows permission errors
- `task_072`: numeric edge case — percentage helper returns unrounded values
- `task_073`: sorting/filtering — top_by_score crashes on missing sort key
- `task_074`: service helper integration — format_name crashes on missing users
- `task_075`: case-insensitive handling — dict lookup is case-sensitive
- `task_076`: multi-file integration — filter_valid imports non-existent is_even
- `task_077`: stateful side effect — IntStack.clear does not reset popped_count
- `task_078`: idempotency — initialize cannot be reset for testing
- `task_079`: validation logic — email validator is too lenient
- `task_080`: config merge — list merger duplicates overlapping entries

### Block 3: 081-090 (P50 bug types, hard)
- `task_081`: parsing edge case — INI parser misses semicolon comments and quotes
- `task_082`: path handling — extension splitter misses compound extensions
- `task_083`: cache key — argument hasher unstable for collections
- `task_084`: optional/default args — table formatter mutates caller's column list
- `task_085`: boundary condition — text wrapper drops words longer than width
- `task_086`: string normalization — accent stripper misses many diacritics
- `task_087`: dict mutation — apply_defaults mutates caller's dictionary
- `task_088`: date boundary — weeks_between mishandles reversed date ranges
- `task_089`: JSON config parsing — nested accessor crashes on missing keys
- `task_090`: CLI argument propagation — repeat command ignores --count

### Block 4: 091-100 (P55 bug types, hard)
- `task_091`: error handling — HTTP fetch helper swallows programming errors
- `task_092`: numeric edge case — clamp silently accepts swapped bounds
- `task_093`: sorting/filtering — prefix filter always case-sensitive
- `task_094`: service helper integration — enrich hard-codes the ID key
- `task_095`: case-insensitive handling — command dispatcher is case-sensitive
- `task_096`: multi-file integration — cart total ignores item quantity
- `task_097`: stateful side effect — rate limiter does not track blocked requests
- `task_098`: idempotency — ensure_seeded silently ignores conflicting seeds
- `task_099`: validation logic — password checker missing special-character requirement
- `task_100`: config merge — layered merge overwrites nested dicts

All 40 tasks are hard-pair friendly (buggy passes public, fails hidden; gold passes both). All gold patches apply cleanly.

## Repair and Verify

```bash
python scripts/p61_repair_and_verify_tasks_061_100.py
```

## Rollout Export

```bash
python scripts/p61_rollout_export_061_100.py
```

Policies: `noop`, `heuristic`, `scripted` (no llm, no external APIs).

Outputs under `data/mini_repo_debug/rollouts/p61_061_100/`.

## Counts

| Metric | P55 Baseline | After P61 | Delta |
|---|---|---|---|
| Active tasks | 60 | 100 | +40 |
| Planned backlog | 40 | 0 | -40 |
| Target total | 100 | 100 | 0 |
| SFT | 60 | >=100 | +40 |
| Preference | 89 | >=100 | +40+ |
| Hard preference | 27 | >=30 | +10+ |

## Checks

```bash
make p61-check
```

## Completion

P61-P100 completes the 100-task Mini-Repo-Debug dataset. The planned backlog is now empty. All SFT, preference, and hard preference thresholds are met.

## Next Recommendation

The 100-task dataset is complete. Next steps could include real training, broader task coverage beyond 100, or integration with external evaluation benchmarks.
