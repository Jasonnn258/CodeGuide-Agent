# HitCounter reset leaves overflow flag set

`HitCounter.reset` should restore the counter to its initial state, including clearing the overflow flag, but it only resets the count.
