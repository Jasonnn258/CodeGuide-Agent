import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import average


def test_average_of_values_still_works():
    assert average([2, 4, 6]) == 4


def test_empty_average_returns_zero():
    assert average([]) == 0.0
