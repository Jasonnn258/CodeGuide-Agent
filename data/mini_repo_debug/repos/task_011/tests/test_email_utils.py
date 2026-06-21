import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from email_utils import normalize_email


def test_lowercases_email_still_works():
    assert normalize_email("Ada@Example.COM") == "ada@example.com"


def test_strips_surrounding_whitespace():
    assert normalize_email("  Ada@Example.COM  ") == "ada@example.com"
