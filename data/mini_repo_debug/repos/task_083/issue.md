# Argument hasher is not stable for collections

`hash_args` should produce the same hash for identical arguments, including when lists, tuples, and dicts are used. Dict ordering should not affect the result.
