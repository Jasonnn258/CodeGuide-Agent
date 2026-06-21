# Raise ConfigError for invalid timeouts

`parse_timeout` is part of config validation. It should return a positive integer timeout, and invalid configs should raise the local `ConfigError` type instead of leaking raw Python exceptions.

Please keep valid parsing behavior but normalize error handling.
