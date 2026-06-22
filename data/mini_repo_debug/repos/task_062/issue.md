# Path resolver does not collapse parent-directory references

`resolve_path` should normalize `..` segments so that `/a/b/../c` resolves to `/a/c`. Going above the root should be clamped.
