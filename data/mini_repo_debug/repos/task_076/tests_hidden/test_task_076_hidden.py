from task_076_lib.filtering import filter_valid


def test_filter_keeps_even_numbers():
    assert filter_valid([1, 2, 3, 4, 5, 6]) == [2, 4, 6]


def test_filter_returns_empty_when_no_evens():
    assert filter_valid([1, 3, 5]) == []
