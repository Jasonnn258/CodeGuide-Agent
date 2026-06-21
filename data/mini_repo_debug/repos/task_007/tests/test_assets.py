import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from assets import asset_path


def test_relative_asset_path_still_joins():
    assert asset_path("/app/static", "img/logo.png") == Path("/app/static/img/logo.png")


def test_leading_slash_stays_under_base_dir():
    assert asset_path("/app/static", "/img/logo.png") == Path("/app/static/img/logo.png")
