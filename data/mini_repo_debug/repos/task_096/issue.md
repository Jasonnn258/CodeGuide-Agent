# Cart total ignores item quantity

`cart_total` should multiply each item's price by its quantity, but `Item` has no `quantity` field and `cart_total` only sums prices.
