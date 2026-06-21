# Normalize product labels consistently

The `normalize_label` helper is used before comparing product labels.

It should normalize user-facing labels into a stable canonical form. The current implementation handles only the simplest case and fails on common formatting differences.

Please fix the implementation without changing the public API.
