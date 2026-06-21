# Percent change uses the wrong denominator

`percent_change(old, new)` should report change relative to the old value. It currently divides by the new value, producing incorrect metrics.
