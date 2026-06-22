# IntStack.clear does not reset pop history

`IntStack.clear` should reset the stack to its initial state, including clearing the internal pop-history list so `popped_count()` returns 0 after clear.
