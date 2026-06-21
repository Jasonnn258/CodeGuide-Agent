import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from access import role_allowed


def test_uppercase_allowed_role_matches_lowercase_input():
    assert role_allowed("viewer", ["ADMIN", "VIEWER"]) is True
    assert role_allowed("owner", ["ADMIN", "VIEWER"]) is False
