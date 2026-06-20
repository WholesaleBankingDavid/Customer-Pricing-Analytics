# Methodology

The MVP follows an incremental analytics path:

1. Profile the available workbook without assuming a fixed schema.
2. Define the target data model for future structured data ingestion.
3. Derive facility-level economics from internal cost and guardrail inputs.
4. Aggregate facility economics to deal level.
5. Estimate win probability from historical commercial won/lost outcomes.
6. Combine expected profit and win probability into expected deal value.
7. Rank active deals for RM review.

The first model should be explainable and conservative. Logistic regression is the preferred baseline. More complex models can be evaluated later, but only if they improve calibrated decision support without obscuring the business logic.

Competitor or market-counterparty price information is excluded from the methodology. The MVP should rely on internal deal economics, internal guardrails, historical outcomes, and RM feedback.
