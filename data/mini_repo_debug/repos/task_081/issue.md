# INI parser does not handle semicolon comments or quoted values

`parse_ini_section` should skip lines starting with `;` (semicolon comments) and strip surrounding double-quotes from values.
