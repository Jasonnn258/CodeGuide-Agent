from task_042_lib.paths import safe_asset_path


def test_keeps_simple_relative_path():
    assert safe_asset_path("images/logo.png") == "images/logo.png"


def test_normalizes_current_directory():
    assert safe_asset_path("images/./logo.png") == "images/logo.png"
