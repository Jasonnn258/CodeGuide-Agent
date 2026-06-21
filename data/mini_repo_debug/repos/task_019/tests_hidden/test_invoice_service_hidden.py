import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_service import make_invoice


def test_tax_on_multiple_items():
    assert make_invoice([{"price": 5}, {"price": 2, "qty": 3}], tax=4) == {"total": 15}
