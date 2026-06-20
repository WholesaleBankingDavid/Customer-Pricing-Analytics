"""Scoring helpers for active deal prioritization."""

import pandas as pd


def score_active_deals(model, df: pd.DataFrame) -> pd.DataFrame:
    """Score active deals with win probability and optional expected deal value."""

    result = df.copy()
    probabilities = model.predict_proba(result)[:, 1]
    result["win_probability"] = probabilities

    if "total_expected_profit" in result.columns:
        result["expected_deal_value"] = (
            result["win_probability"] * result["total_expected_profit"]
        )
        sort_columns = ["expected_deal_value", "win_probability"]
    else:
        sort_columns = ["win_probability"]

    result = result.sort_values(sort_columns, ascending=False).reset_index(drop=True)
    result["priority_rank"] = result.index + 1
    return result
