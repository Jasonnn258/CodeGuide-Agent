# Username validator rejects names with surrounding whitespace

`is_valid_username` should accept names that are valid after trimming whitespace, but it treats leading or trailing spaces as invalid characters.
