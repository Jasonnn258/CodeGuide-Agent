# Invoice totals ignore tax helper behavior

The invoice service has a helper for tax calculation, but totals currently ignore tax entirely. The tax helper also truncates fractional tax amounts instead of applying normal rounding.

Please fix the integration so invoice totals include the rounded tax amount.
