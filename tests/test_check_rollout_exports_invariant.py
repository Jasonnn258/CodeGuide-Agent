"""Regression test for the monotonic-growth invariant in check_rollout_exports.

Background: p{34,38,42,50,55,61}_check_rollout_exports.py previously compared
phase-summary snapshot counts against live counts with `!=`. Because later
phases legitimately grow the live data, those snapshots became stale and the
checks false-failed. The fix replaces `!=` with `>`: the check should only
error when a snapshot exceeds the live count (data loss), not when the live
count has grown (expected monotonic growth).

This test locks in the new behavior so a future revert to `!=` is caught.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

CHECK_SCRIPTS = (
    "p34_check_rollout_exports.py",
    "p38_check_rollout_exports.py",
    "p42_check_rollout_exports.py",
    "p50_check_rollout_exports.py",
    "p55_check_rollout_exports.py",
    "p61_check_rollout_exports.py",
)


def _read_script(name: str) -> str:
    return (SCRIPTS_DIR / name).read_text(encoding="utf-8")


def test_scripts_use_monotonic_growth_not_equality() -> None:
    """Each check script must compare snapshot > live (not snapshot != live)."""
    for name in CHECK_SCRIPTS:
        source = _read_script(name)
        assert "exceeds live" in source, f"{name} missing 'exceeds live' guard"
        assert "does not match" not in source, (
            f"{name} still uses stale 'does not match' comparison"
        )
        bank_match = re.search(
            r'preference_bank_total["\)\]\s]*>\s*len\(bank_rows\)', source
        )
        assert bank_match, (
            f"{name} must compare preference_bank_total > len(bank_rows)"
        )
        if "sft_total" in source:
            sft_match = re.search(
                r'sft_total["\)\]\s]*>\s*len\(package_sft\)', source
            )
            assert sft_match, (
                f"{name} must compare sft_total > len(package_sft)"
            )
        assert not re.search(
            r'preference_bank_total["\)\]\s]*!=\s*len\(bank_rows\)', source
        ), f"{name} reverted to != comparison"
        if "sft_total" in source:
            assert not re.search(
                r'sft_total["\)\]\s]*!=\s*len\(package_sft\)', source
            ), f"{name} reverted to != comparison"


def test_behavioral_pass_when_snapshot_equals_live(tmp_path: Path) -> None:
    """Snapshot == live (no growth since phase end) must PASS."""
    _run_check_against_fixture(tmp_path, snapshot_bank=5, live_bank=5, expect_pass=True)


def test_behavioral_pass_when_live_grew_past_snapshot(tmp_path: Path) -> None:
    """Live count grew past snapshot (later phase added data) must PASS."""
    _run_check_against_fixture(tmp_path, snapshot_bank=5, live_bank=20, expect_pass=True)


def test_behavioral_fail_when_snapshot_exceeds_live(tmp_path: Path) -> None:
    """Snapshot > live (data loss) must FAIL."""
    _run_check_against_fixture(tmp_path, snapshot_bank=20, live_bank=5, expect_pass=False)


def _run_check_against_fixture(
    tmp_path: Path,
    *,
    snapshot_bank: int,
    live_bank: int,
    expect_pass: bool,
) -> None:
    """Run p34's check logic against a synthetic fixture."""
    fixture_root = tmp_path / "data" / "mini_repo_debug"
    bank_dir = fixture_root / "preference_bank"
    bank_dir.mkdir(parents=True)
    # p34 checks task_021..task_025; the first 5 bank rows must cover those ids.
    required_ids = ("task_021", "task_022", "task_023", "task_024", "task_025")
    bank_ids = list(required_ids) + [
        f"task_0{i}" for i in range(len(required_ids), live_bank)
    ][: max(0, live_bank - len(required_ids))]
    bank_ids = bank_ids[:live_bank]
    (bank_dir / "preference_candidates.jsonl").write_text(
        "\n".join(json.dumps({"task_id": tid}) for tid in bank_ids)
        + "\n",
        encoding="utf-8",
    )

    pkg_dir = fixture_root / "train_package"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "preference_train.jsonl").write_text(
        "\n".join(json.dumps({"task_id": tid}) for tid in bank_ids)
        + "\n",
        encoding="utf-8",
    )
    (pkg_dir / "preference_eval.jsonl").write_text("", encoding="utf-8")

    traj_dir = fixture_root / "trajectories"
    traj_dir.mkdir(parents=True)
    for tid in ("task_021", "task_022", "task_023", "task_024", "task_025"):
        (traj_dir / f"{tid}_noop.jsonl").write_text(
            json.dumps({"event": "step"}) + "\n", encoding="utf-8"
        )

    summary_dir = fixture_root / "rollouts" / "p34_021_025"
    summary_dir.mkdir(parents=True)
    (summary_dir / "summary.json").write_text(
        json.dumps(
            {"after_counts": {"preference_bank_total": snapshot_bank}}
        ),
        encoding="utf-8",
    )

    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(REPO_ROOT),
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "p34_check_rollout_exports.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if expect_pass:
        assert result.returncode == 0, (
            f"expected PASS but script failed: rc={result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "PASS" in result.stdout
    else:
        assert result.returncode == 1, (
            f"expected FAIL but script passed: rc={result.returncode}\n"
            f"stdout:\n{result.stdout}"
        )
        assert "FAIL" in result.stdout
        assert "data loss" in result.stdout


if __name__ == "__main__":
    import inspect

    funcs = [
        v
        for k, v in list(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failed = 0
    for fn in funcs:
        try:
            sig = inspect.signature(fn)
            kwargs = {}
            for param in sig.parameters.values():
                if param.name == "tmp_path":
                    import tempfile

                    kwargs["tmp_path"] = Path(tempfile.mkdtemp())
            fn(**kwargs)
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
