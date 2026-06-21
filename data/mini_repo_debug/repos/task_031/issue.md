# Validate configured network ports

`parse_port` should accept a missing port by using the default, but invalid ports should raise `ConfigError` instead of leaking raw exceptions or accepting impossible values.
