import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from email_utils import normalize_email


def test_newline_and_tab_whitespace_are_stripped():
    assert normalize_email("\tGRACE@Example.org\n") == "grace@example.org"
