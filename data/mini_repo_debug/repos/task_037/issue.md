# Batch helper leaks state across calls

`add_batch_item` should return a new batch with the item added. Separate calls without an explicit batch must not share state, and caller-provided lists should not be mutated.
