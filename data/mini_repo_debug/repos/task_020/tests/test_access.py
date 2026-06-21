import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from access import role_allowed


def test_exact_role_match_still_works():
    assert role_allowed("admin", ["admin", "editor"]) is True


def test_role_match_is_case_insensitive():
    assert role_allowed("Admin", ["admin", "editor"]) is True
