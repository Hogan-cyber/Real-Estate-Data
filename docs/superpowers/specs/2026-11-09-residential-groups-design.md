# Built-in residential indicator groups

The user wants the already demonstrated grouping code inside the package: a few
lines should show the whole dataset and read one or several groups by date.

Use the existing `Residential` reader and the same 14 groups. Add `overview()`;
add `group` and `frequency` keyword selectors to the constructor, `history()`,
`catalog()` and `observations()`. `catalog()` adds a `group` column. Group names
accept their displayed spelling or a case-insensitive underscore alias such as
`price_indices`. A group iterable means union; group, frequency and explicit IDs
intersect. Method selectors override the corresponding constructor selector.

`overview()` reports indicators, source records, non-null values and recorded
date coverage, indexed by group and frequency. It has no date filter: use
`history(start=..., end=...)` for a dated analysis. Existing money-lender results
and the three model input shares remain separate from observed bank mortgages.
Unrecognized future IDs stay visible as `Other / new indicators`.

Retain numeric values, original observation metadata, inclusive dates, missing
values, shared bounded cache, explicit refresh and lazy imports. Reject unknown
or empty selectors clearly; a date range without records still returns typed
empty history columns. No additional dependencies or collector changes.

Ship 0.6.0 and replace the copied grouping code in README, the Python guide and
examples. A small package workflow publishes a tested wheel independently of
official-data collection so a source outage cannot prevent a reader upgrade.
Leave the existing unpublished dashboard work outside this publication.

The user explicitly selected package integration after testing the standalone
approach; no additional interface choice is needed to implement this scope.
