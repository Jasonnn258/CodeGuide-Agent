import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_loader import load_config


def test_json_still_loads(tmp_path):
    config = tmp_path / "app.json"
    config.write_text('{"name": "json", "retries": 2}', encoding="utf-8")

    assert load_config(str(config)) == {"name": "json", "retries": 2}


def test_yml_extension_loads(tmp_path):
    config = tmp_path / "app.yml"
    config.write_text("name: hidden\nretries: 5\n", encoding="utf-8")

    assert load_config(str(config)) == {"name": "hidden", "retries": 5}
