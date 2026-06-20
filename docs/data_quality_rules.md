# Data Quality Rules

## ID Integrity

- Silver customers deduplicate CRM accounts using latest `source_extract_ts`.
- Silver deals reference existing Silver customers.
- Silver facilities reference existing Silver deals.
- Stable synthetic IDs are generated for customers, deals, and facilities.

## Duplicate Handling

Bronze duplicates are intentional. Silver keeps the latest record by source identifier and extract timestamp where applicable.

## Missing Values

Bronze optional fields may be missing. Silver parses or defaults selected operational values, such as expected utilization, while preserving missing business context where appropriate.

## Status Harmonization

CRM stages and LOS statuses are harmonized into active, closed won, closed lost, or withdrawn states. Active deals must not have a final outcome.

## Final Quote Selection

Final quote selection is facility-level:

1. Use the latest approved or submitted quote version.
2. If no approved or submitted version exists, use the latest available quote and flag a warning.

## Outcome Rules

- Closed commercial deals have `won` or `lost` outcomes.
- Active deals have no `deal_outcome`.
- Withdrawn or non-commercial lost reasons can be excluded from model training through `commercial_relevance_flag = false`.

## No Leakage Rules

Gold training data excludes post-outcome leakage:

- no lost reason as a model feature
- no decision-date-derived features
- no active deals
- only commercial won/lost outcomes

## No Competitor Feature Rule

No medallion table may contain competitor pricing, competitor bank, competitor margin, or equivalent fields. The MVP is pricing guidance based on internal data, not competitive price matching.
