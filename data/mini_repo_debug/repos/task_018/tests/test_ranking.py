import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ranking import top_active


def test_filters_inactive_users():
    users = [{"name": "Ada", "score": 5, "active": True}, {"name": "Grace", "score": 9, "active": False}]
    assert top_active(users, 2) == ["Ada"]


def test_returns_highest_scoring_active_users_first():
    users = [
        {"name": "Ada", "score": 5, "active": True},
        {"name": "Linus", "score": 8, "active": True},
        {"name": "Grace", "score": 9, "active": False},
    ]
    assert top_active(users, 2) == ["Linus", "Ada"]
