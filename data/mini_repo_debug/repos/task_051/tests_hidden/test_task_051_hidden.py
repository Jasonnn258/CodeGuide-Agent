from task_051_lib.parser import parse_int


def test_rejects_non_string():
    try:
        parse_int(None)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for None input")


def test_rejects_list_input():
    try:
        parse_int([1, 2, 3])
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for list input")
