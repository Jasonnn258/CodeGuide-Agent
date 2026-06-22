# format_name crashes on missing users

`format_name` should return `"Unknown"` when the user does not exist, instead of crashing with an attribute error.
