"""Validation helpers for idealized deal datasets."""

from dataclasses import dataclass

import pandas as pd

REQUIRED_DEAL_COLUMNS = {
    "deal_id",
    "customer_id",
    "deal_status",
    "deal_outcome",
    "commercial_relevance_flag",
}

RECOMMENDED_DEAL_COLUMNS = {
    "deal_type",
    "offer_date",
    "decision_date",
    "expected_close_date",
    "lost_reason",
}


@dataclass(frozen=True)
class ValidationResult:
    """Validation result that warns instead of failing hard."""

    is_valid: bool
    missing_columns: list[str]
    warnings: list[str]


def validate_deal_dataset(df: pd.DataFrame) -> ValidationResult:
    """Validate an idealized deal dataset without assuming production readiness."""

    columns = set(df.columns)
    missing = sorted(REQUIRED_DEAL_COLUMNS - columns)
    warnings: list[str] = []

    missing_recommended = sorted(RECOMMENDED_DEAL_COLUMNS - columns)
    if missing_recommended:
        warnings.append(f"Missing recommended columns: {missing_recommended}")

    if "deal_outcome" in columns:
        observed = set(df["deal_outcome"].dropna().astype(str).str.lower().unique())
        unexpected = sorted(observed - {"won", "lost"})
        if unexpected:
            warnings.append(f"Unexpected deal_outcome values: {unexpected}")

    if "commercial_relevance_flag" in columns and df["commercial_relevance_flag"].isna().any():
        warnings.append("commercial_relevance_flag contains missing values")

    if "deal_id" in columns and df["deal_id"].duplicated().any():
        warnings.append("deal_id contains duplicates")

    return ValidationResult(
        is_valid=not missing,
        missing_columns=missing,
        warnings=warnings,
    )
