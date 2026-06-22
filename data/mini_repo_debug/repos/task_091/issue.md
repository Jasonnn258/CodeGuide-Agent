# HTTP fetch helper swallows programming errors

`fetch_with_timeout` should catch network and URL errors gracefully, but must not suppress `TypeError` or `AttributeError` caused by incorrect arguments.
