from task_062_lib.resolve import resolve_path


def test_parent_is_resolved():
    assert resolve_path("/a/b/c", "../d") == "/a/b/d"


def test_double_parent_is_resolved():
    assert resolve_path("/a/b/c", "../../x") == "/a/x"
