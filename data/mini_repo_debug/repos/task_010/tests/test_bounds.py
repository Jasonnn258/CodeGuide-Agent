import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bounds import clamp_index


def test_in_range_index_still_returns_itself():
    assert clamp_index(2, 5) == 2


def test_index_equal_to_size_clamps_to_last_valid_index():
    assert clamp_index(5, 5) == 4
