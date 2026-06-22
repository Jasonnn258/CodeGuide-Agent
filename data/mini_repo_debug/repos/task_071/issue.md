# File reader silently swallows permission errors

`read_file` should return an empty string when the file does not exist, but must raise `PermissionError` for unreadable files.
