# Nested JSON accessor crashes on missing intermediate keys

`get_nested` should return `None` when any segment of the dotted path is absent, instead of raising `KeyError`.
