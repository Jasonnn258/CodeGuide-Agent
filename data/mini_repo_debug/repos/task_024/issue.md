# Add a tag without leaking mutable state

The `add_tag` helper returns a list of tags with a new tag appended.

It should work both when no existing tags are provided and when the caller passes an existing list. The caller's list should not be mutated.

Please fix the implementation without changing the public API.
