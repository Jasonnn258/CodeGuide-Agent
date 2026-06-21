# Window helper drops exact boundary slices

`take_window` should allow a slice that ends exactly at the end of the list, but reject windows that overrun the list.
