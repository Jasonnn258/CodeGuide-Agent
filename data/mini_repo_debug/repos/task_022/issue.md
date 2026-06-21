# Safely resolve user-provided report paths

The report loader joins a base directory with a user-provided path.

The helper should keep paths inside the base directory and normalize harmless relative path syntax. It should reject paths that escape the base directory.

Please fix the helper without changing its function signature.
