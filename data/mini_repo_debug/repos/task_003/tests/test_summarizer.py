import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from summarizer import total_amount


def test_normal_csv_still_sums():
    assert total_amount("name,amount\napple,2\npear,3\n") == 5


def test_ignores_empty_amount_rows():
    csv_text = "name,amount\napple,2\nbanana,\npear,3\n"

    assert total_amount(csv_text) == 5
