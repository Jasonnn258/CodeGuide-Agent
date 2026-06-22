from task_082_lib.extension import split_extension


def test_simple_extension():
    assert split_extension("readme.txt") == ("readme", ".txt")


def test_no_extension():
    assert split_extension("Makefile") == ("Makefile", "")


def test_multiple_dots_returns_last_ext():
    assert split_extension("image.png.jpg") == ("image.png", ".jpg")
