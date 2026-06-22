# initialize cannot be reset for testing

`initialize` correctly creates each value only once, but there is no way to reset the global state between tests without restarting the process. A `reset_initialized` function is needed.
