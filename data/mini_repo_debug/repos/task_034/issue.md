# Order totals ignore the discount helper

The order service imports `apply_discount`, but totals currently ignore discounts. The helper should also round fractional discounts consistently.
