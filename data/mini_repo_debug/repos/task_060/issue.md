# Config merge overwrites nested sections

`merge_config` should deep-merge nested dictionaries so that overriding a single key inside a nested section preserves sibling keys, but the current flat update replaces the entire subsection.
