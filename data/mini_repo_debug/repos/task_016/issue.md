# Missing users raise an exception

Looking up a user id that is not present should return `None` instead of raising `StopIteration`.
