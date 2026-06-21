import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jsonl_loader import load_json_lines


def test_whitespace_only_lines_are_skipped():
    assert load_json_lines('{"name": "a"}\n   \n{"name": "b"}\n') == [{"name": "a"}, {"name": "b"}]
