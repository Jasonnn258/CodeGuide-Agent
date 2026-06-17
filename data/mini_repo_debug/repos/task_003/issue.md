# Empty CSV amount rows break totals

CSV exports can contain rows where `amount` is empty. The summarizer should ignore empty amount rows and keep summing valid values.
