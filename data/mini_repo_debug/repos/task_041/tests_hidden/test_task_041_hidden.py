from task_041_lib.parser import parse_assignment


def test_value_may_contain_equals():
    assert parse_assignment("token=a=b=c") == ("token", "a=b=c")
