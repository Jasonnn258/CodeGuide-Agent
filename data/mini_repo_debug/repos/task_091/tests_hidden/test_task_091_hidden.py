from task_091_lib.gateway import fetch_with_timeout


def test_none_url_is_not_silenced():
    try:
        fetch_with_timeout(None)  # type: ignore
    except Exception:
        pass
    else:
        raise AssertionError("expected exception for None url")


def test_invalid_timeout_type_raises():
    try:
        fetch_with_timeout("http://example.com", timeout="fast")  # type: ignore
    except Exception:
        pass
    else:
        raise AssertionError("expected exception for string timeout")
