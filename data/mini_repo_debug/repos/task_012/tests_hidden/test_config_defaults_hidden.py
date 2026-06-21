import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_defaults import merge_defaults


def test_reusing_defaults_for_multiple_configs_is_safe():
    defaults = {"debug": False, "retries": 2}
    assert merge_defaults({"debug": True}, defaults) == {"debug": True, "retries": 2}
    assert merge_defaults({"retries": 4}, defaults) == {"debug": False, "retries": 4}
