import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from users import find_user


def test_empty_user_list_returns_none():
    assert find_user([], "nobody") is None
