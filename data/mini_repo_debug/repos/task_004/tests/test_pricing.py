import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pricing import PriceService


def test_reuses_cached_exact_item_region():
    service = PriceService({("book", "us"): 10})

    assert service.get_price("book", "us") == 10
    service.prices[("book", "us")] = 99
    assert service.get_price("book", "us") == 10


def test_cache_key_includes_region():
    service = PriceService({("book", "us"): 10, ("book", "eu"): 12})

    assert service.get_price("book", "us") == 10
    assert service.get_price("book", "eu") == 12
