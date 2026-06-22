# filter_valid imports a function that does not exist

`filter_valid` imports `is_even` from the validator module, but `is_even` is not defined there. The fix should add `is_even` to the validator.
