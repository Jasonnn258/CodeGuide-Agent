from task_046_lib.slugs import slugify


def test_punctuation_and_repeated_spaces():
    assert slugify("Hello,   World!") == "hello-world"
