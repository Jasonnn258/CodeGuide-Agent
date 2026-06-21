# Asset paths must stay inside the asset root

`safe_asset_path` should normalize ordinary relative paths, but reject absolute paths and parent-directory traversal.
