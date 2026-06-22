# Page count drops trailing items

`page_count` should return the ceiling of `total / per_page` so that a partial last page counts as a full page.
