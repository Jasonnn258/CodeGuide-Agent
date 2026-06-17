import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pricing import PriceService


def test_cache_reuses_exact_item_region():
    service = PriceService({("book", "us"): 10, ("pen", "us"): 2})

    assert service.get_price("book", "us") == 10
    service.prices[("book", "us")] = 99
    assert service.get_price("book", "us") == 10
    assert service.get_price("pen", "us") == 2
