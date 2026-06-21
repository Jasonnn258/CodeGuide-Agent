# Tags leak between calls

Calling the tag collector without an explicit initial tag list should not reuse tags from earlier calls.
