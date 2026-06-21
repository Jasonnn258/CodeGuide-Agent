# Parse JSON config files used by operators

`load_config` is used for small JSON config snippets pasted into an admin tool.

It should keep supporting ordinary JSON, and it should also tolerate common config-file conveniences such as comment-only lines and trailing commas.

Please fix the parser without changing the public API.
