# Version parser crashes on pre-release suffixes

`parse_version` should strip pre-release labels such as `-beta` or `-rc1` before parsing the numeric parts.
