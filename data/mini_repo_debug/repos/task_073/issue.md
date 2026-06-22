# top_by_score crashes when items are missing the sort key

`top_by_score` should treat missing keys as zero when sorting, instead of raising `KeyError`.
