# Integer parser swallows type errors

`parse_int` should convert numeric strings to integers and return `None` for unparseable strings, but must raise `TypeError` when the input is not a string at all.
