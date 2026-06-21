# Optional flag list leaks state

`add_flag` should create a fresh list when no list is supplied and should not mutate caller-provided lists.
