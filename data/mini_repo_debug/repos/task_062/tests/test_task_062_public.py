from task_062_lib.resolve import resolve_path


def test_simple_child():
    assert resolve_path("/a/b", "c") == "/a/b/c"


def test_absolute_override():
    assert resolve_path("/a/b", "/x/y") == "/x/y"
