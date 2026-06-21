import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from due_dates import is_expired


def test_future_date_is_not_expired():
    assert is_expired("2026-01-03", "2026-01-02") is False


def test_due_today_is_expired():
    assert is_expired("2026-01-02", "2026-01-02") is True
