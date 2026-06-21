import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from assets import asset_path


def test_multiple_leading_slashes_are_trimmed():
    assert asset_path("/srv/assets", "//css/app.css") == Path("/srv/assets/css/app.css")
