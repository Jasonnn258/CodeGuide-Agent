import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jsonl_loader import load_json_lines


def test_normal_json_lines_still_load():
    assert load_json_lines('{"id": 1}\n{"id": 2}\n') == [{"id": 1}, {"id": 2}]


def test_blank_lines_are_skipped():
    assert load_json_lines('{"id": 1}\n\n{"id": 2}\n') == [{"id": 1}, {"id": 2}]
