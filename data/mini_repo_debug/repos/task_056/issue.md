# Stats report crashes on empty input

`report` should return zeroed statistics for an empty list, but `aggregate` returns a count of zero, causing a division by zero when computing the mean.
