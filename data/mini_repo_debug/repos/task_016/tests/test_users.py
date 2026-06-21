import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from users import find_user


def test_existing_user_is_returned():
    users = [{"id": "1", "name": "Ada"}, {"id": "2", "name": "Grace"}]
    assert find_user(users, "2") == {"id": "2", "name": "Grace"}


def test_missing_user_returns_none():
    assert find_user([{"id": "1", "name": "Ada"}], "missing") is None
