# Clamp function silently accepts swapped bounds

`clamp` should raise `ValueError` when `low > high` so callers do not silently get an incorrectly constrained value when the bounds are specified in reverse order.
