import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pair_parser import parse_pairs


def test_token_value_keeps_multiple_equals_signs():
    assert parse_pairs("token=a=b=c\nmode=fast\n") == {"token": "a=b=c", "mode": "fast"}
