# JSON list accessor returns None for missing keys

`get_list` should return an empty list when the requested key is absent from the configuration, never `None`.
