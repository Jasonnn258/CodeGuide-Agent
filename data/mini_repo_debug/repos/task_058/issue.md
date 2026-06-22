# ensure_dir is not idempotent

`ensure_dir` should safely create a directory and succeed silently when the directory already exists, but it raises an error on the second call.
