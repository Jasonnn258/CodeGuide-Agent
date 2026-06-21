# Assignment parser rejects values containing equals signs

`parse_assignment` should split only on the first equals sign so configuration values such as tokens or URLs can contain `=` characters.
