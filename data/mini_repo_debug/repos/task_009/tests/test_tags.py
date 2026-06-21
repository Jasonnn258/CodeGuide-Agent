import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tags import collect_tags


def test_collects_unique_tags_from_one_call():
    assert collect_tags([{"tag": "red"}, {"tag": "red"}, {"tag": "blue"}], []) == ["red", "blue"]


def test_default_tags_do_not_leak_between_calls():
    assert collect_tags([{"tag": "red"}]) == ["red"]
    assert collect_tags([{"tag": "blue"}]) == ["blue"]
