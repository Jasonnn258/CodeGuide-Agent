from task_042_lib.paths import safe_asset_path


def test_rejects_parent_traversal():
    try:
        safe_asset_path("../secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rejects_absolute_path():
    try:
        safe_asset_path("/tmp/secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
