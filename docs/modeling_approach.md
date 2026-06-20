# Modeling Approach

## Target Variable

The initial target variable is:

```text
deal_outcome = won/lost
```

Deals that were rejected for technical, risk, operational, or non-commercial reasons should be excluded from win/loss modeling when `commercial_relevance_flag = false`.

## Feature Boundaries

The model must not use competitor price features. Inputs should focus on internal economics, product mix, tenor, rating, customer segment, deal type, and historical commercial outcomes.

## Modeling Path

1. Start with descriptive win/loss analysis.
2. Train an explainable baseline model using logistic regression.
3. Optionally evaluate gradient boosting or random forest as performance benchmarks.
4. Check calibration before using probabilities in expected value calculations.

## Leakage Controls

Use a time-based split or grouped split by customer or deal where possible. Avoid leakage from future outcomes, post-decision fields, or duplicated customer exposures across train and test folds.

## Metrics

- ROC-AUC
- PR-AUC
- Brier Score
- Calibration Curve
- Confusion Matrix
- Lift by decile

## Interpretation

The model estimates commercial win probability. It is not an optimal-price engine. It supports pricing guidance and deal prioritization for human decision-making.
