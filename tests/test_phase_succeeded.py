"""Tests for the idempotent phase-succeeded computation (P0-2 fix).

Source: docs/ROADMAP_CONTEXT_RAG_TRAINING.md P0-2 — p61_succeeded must be True
when the final state meets thresholds and no rollout failures occurred, even
when refresh commands produced zero deltas (the idempotent re-run case).
"""

from __future__ import annotations

from codeguide_agent.eval.phase_succeeded import (
    DEFAULT_THRESHOLDS,
    compute_phase_succeeded,
)


def _after_counts_meeting_thresholds() -> dict[str, int]:
    return {
        "sft_total": DEFAULT_THRESHOLDS["sft_total"],
        "preference_total": DEFAULT_THRESHOLDS["preference_total"],
        "preference_bank_total": DEFAULT_THRESHOLDS["preference_bank_total"],
        "hard_preference_total": DEFAULT_THRESHOLDS["hard_preference_total"],
        "active_task_count": DEFAULT_THRESHOLDS["task_total"],
        "planned_backlog_count": 0,
    }


def test_succeeds_when_thresholds_met_and_no_failures():
    """Idempotent re-run: thresholds met, no failures, deltas may be zero."""
    after = _after_counts_meeting_thresholds()
    assert compute_phase_succeeded([], after) is True


def test_succeeds_with_zero_deltas_idempotent_case():
    """Re-running a phase whose data is already canonical must not fail."""
    after = _after_counts_meeting_thresholds()
    failures: list[dict] = []
    assert compute_phase_succeeded(failures, after) is True


def test_fails_when_sft_below_threshold():
    after = _after_counts_meeting_thresholds()
    after["sft_total"] = DEFAULT_THRESHOLDS["sft_total"] - 1
    assert compute_phase_succeeded([], after) is False


def test_fails_when_hard_preference_below_threshold():
    after = _after_counts_meeting_thresholds()
    after["hard_preference_total"] = DEFAULT_THRESHOLDS["hard_preference_total"] - 1
    assert compute_phase_succeeded([], after) is False


def test_fails_when_task_total_below_threshold():
    after = _after_counts_meeting_thresholds()
    after["active_task_count"] = DEFAULT_THRESHOLDS["task_total"] - 1
    after["planned_backlog_count"] = 0
    assert compute_phase_succeeded([], after) is False


def test_fails_when_failures_present_even_if_thresholds_met():
    after = _after_counts_meeting_thresholds()
    failures = [{"task_id": "task_061", "policy": "noop", "error": "missing_task"}]
    assert compute_phase_succeeded(failures, after) is False


def test_succeeds_with_active_plus_planned_meeting_threshold():
    after = _after_counts_meeting_thresholds()
    after["active_task_count"] = 50
    after["planned_backlog_count"] = 50
    assert compute_phase_succeeded([], after) is True


def test_fails_when_thresholds_meet_but_neither_active_nor_planned():
    after = _after_counts_meeting_thresholds()
    after["active_task_count"] = 0
    after["planned_backlog_count"] = 0
    assert compute_phase_succeeded([], after) is False


def test_custom_thresholds_respected():
    after = _after_counts_meeting_thresholds()
    custom = dict(DEFAULT_THRESHOLDS)
    custom["sft_total"] = 200
    assert compute_phase_succeeded([], after, thresholds=custom) is False
    after["sft_total"] = 200
    assert compute_phase_succeeded([], after, thresholds=custom) is True


def test_missing_keys_treated_as_zero():
    after = {"sft_total": 999}
    assert compute_phase_succeeded([], after) is False


if __name__ == "__main__":
    import sys
    funcs = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
