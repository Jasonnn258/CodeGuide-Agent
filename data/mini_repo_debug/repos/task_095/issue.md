# Command dispatcher is case-sensitive

`dispatch` should find commands regardless of the casing used at registration or invocation, so `"HELP"` and `"help"` resolve to the same handler.
