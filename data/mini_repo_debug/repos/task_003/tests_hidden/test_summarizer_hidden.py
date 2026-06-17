import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from summarizer import total_amount


def test_strips_amount_whitespace():
    csv_text = "name,amount\napple, 2 \nbanana,3\n"

    assert total_amount(csv_text) == 5


def test_normal_csv_still_sums():
    assert total_amount("name,amount\na,1\nb,4\n") == 5
