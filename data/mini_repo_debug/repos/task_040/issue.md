# Config overrides should merge nested dictionaries

`merge_config` should apply overrides without mutating defaults. Nested dictionaries should merge recursively so unspecified nested defaults are preserved.
