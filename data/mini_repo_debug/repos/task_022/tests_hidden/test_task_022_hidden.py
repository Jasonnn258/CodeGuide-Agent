from task_022_lib.paths import safe_join


def test_rejects_parent_directory_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    try:
        safe_join(str(base), "../secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rejects_absolute_escape(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    try:
        safe_join(str(base), str(outside))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
