import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tags import collect_tags


def test_explicit_starting_tags_are_copied_and_extended():
    base = ["seed"]
    assert collect_tags([{"tag": "new"}], base) == ["seed", "new"]
    assert base == ["seed"]
