from task_082_lib.extension import split_extension


def test_known_compound_tar_gz():
    assert split_extension("backup.tar.gz") == ("backup", ".tar.gz")


def test_known_compound_tar_bz2():
    assert split_extension("data.tar.bz2") == ("data", ".tar.bz2")


def test_unknown_double_is_split_normally():
    assert split_extension("image.png.jpg") == ("image.png", ".jpg")
