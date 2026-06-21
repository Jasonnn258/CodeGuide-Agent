import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_defaults import merge_defaults


def test_user_config_overrides_defaults():
    assert merge_defaults({"retries": 5}, {"retries": 2, "timeout": 10}) == {"retries": 5, "timeout": 10}


def test_defaults_are_not_mutated():
    defaults = {"retries": 2, "timeout": 10}
    merge_defaults({"retries": 5}, defaults)
    assert defaults == {"retries": 2, "timeout": 10}
