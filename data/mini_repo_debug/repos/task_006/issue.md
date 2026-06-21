# Values containing equals signs fail

The pair parser should accept values that contain `=` characters, such as URLs and tokens. It currently crashes instead of keeping the full value.
