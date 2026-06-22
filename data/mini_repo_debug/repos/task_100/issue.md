# Layered config merge overwrites nested dicts

`layered_merge` correctly concatenates list values across layers, but it should also deep-merge nested dict values instead of overwriting them.
