import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from due_dates import is_expired


def test_past_date_is_expired_and_future_is_not():
    assert is_expired("2025-12-31", "2026-01-02") is True
    assert is_expired("2026-02-01", "2026-01-02") is False
