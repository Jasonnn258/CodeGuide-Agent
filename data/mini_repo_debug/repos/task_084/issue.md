# Table formatter mutates the caller's column list

`format_table` should not modify the list passed as `columns`. When the user passes an explicit column list, it should be safe to reuse.
