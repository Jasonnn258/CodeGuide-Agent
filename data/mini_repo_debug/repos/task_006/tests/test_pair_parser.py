import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pair_parser import parse_pairs


def test_simple_pairs_still_parse():
    assert parse_pairs("host=localhost\nport=8080\n") == {"host": "localhost", "port": "8080"}


def test_value_may_contain_equals_signs():
    assert parse_pairs("url=https://example.test?a=1\n") == {"url": "https://example.test?a=1"}
