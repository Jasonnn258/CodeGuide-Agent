from task_046_lib.slugs import slugify


def test_simple_words():
    assert slugify("Hello World") == "hello-world"


def test_outer_whitespace():
    assert slugify("  Alpha  ") == "alpha"
