import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ranking import top_active


def test_limit_applies_after_descending_sort():
    users = [
        {"name": "A", "score": 1, "active": True},
        {"name": "B", "score": 3, "active": True},
        {"name": "C", "score": 2, "active": True},
    ]
    assert top_active(users, 1) == ["B"]
