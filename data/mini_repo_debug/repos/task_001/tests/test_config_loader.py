import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_loader import load_config


def test_loads_json_config(tmp_path):
    config = tmp_path / "app.json"
    config.write_text('{"name": "demo", "retries": 2}', encoding="utf-8")

    assert load_config(str(config)) == {"name": "demo", "retries": 2}


def test_loads_yaml_config(tmp_path):
    config = tmp_path / "app.yaml"
    config.write_text("name: demo\nretries: 3\nenabled: true\n", encoding="utf-8")

    assert load_config(str(config)) == {"name": "demo", "retries": 3, "enabled": True}
