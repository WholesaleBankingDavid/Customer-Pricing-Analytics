"""Data quality checks for medallion demo data."""

from __future__ import annotations

import pandas as pd

from customer_pricing_analytics.medallion.schemas import BRONZE_TABLES, GOLD_TABLES, SILVER_TABLES, FORBIDDEN_COMPETITOR_TERMS


def row_counts(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Return row counts by table name."""

    return {name: int(len(df)) for name, df in tables.items()}


def competitor_column_violations(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Return column names that look like forbidden competitor data."""

    violations: list[str] = []
    for table_name, df in tables.items():
        for column in df.columns:
            if any(term in column.lower() for term in FORBIDDEN_COMPETITOR_TERMS):
                violations.append(f"{table_name}.{column}")
    return violations


def bronze_quality_summary(bronze: dict[str, pd.DataFrame]) -> dict:
    """Summarize intentional Bronze data quality characteristics."""

    accounts = bronze[BRONZE_TABLES["crm_accounts"]]
    facilities = bronze[BRONZE_TABLES["los_facilities"]]
    return {
        "duplicate_crm_account_rows": int(accounts["crm_account_id"].duplicated().sum()),
        "duplicate_facility_rows": int(facilities["facility_source_id"].duplicated().sum()),
        "missing_region_rows": int(accounts["region_raw"].isna().sum()),
        "missing_expected_utilisation_rows": int(
            facilities["expected_utilisation_raw"].astype(str).str.lower().isin(["n/a", "nan", "none"]).sum()
        ),
    }


def silver_quality_summary(silver: dict[str, pd.DataFrame]) -> dict:
    """Summarize key Silver integrity checks."""

    customers = silver[SILVER_TABLES["customers"]]
    deals = silver[SILVER_TABLES["deals"]]
    facilities = silver[SILVER_TABLES["facilities"]]
    return {
        "duplicate_customer_ids": int(customers["customer_id"].duplicated().sum()),
        "deals_missing_customer_reference": int((~deals["customer_id"].isin(customers["customer_id"])).sum()),
        "facilities_missing_deal_reference": int((~facilities["deal_id"].isin(deals["deal_id"])).sum()),
        "active_deals_with_outcome": int(deals["deal_status"].eq("active").fillna(False).mul(deals["deal_outcome"].notna()).sum()),
    }


def gold_quality_summary(gold: dict[str, pd.DataFrame]) -> dict:
    """Summarize Gold mart readiness checks."""

    training = gold[GOLD_TABLES["deal_training_dataset"]]
    active = gold[GOLD_TABLES["active_deal_scoring_dataset"]]
    facility = gold[GOLD_TABLES["facility_economics"]]
    return {
        "training_deals": int(len(training)),
        "active_scoring_deals": int(len(active)),
        "facility_economics_rows": int(len(facility)),
        "training_outcome_values": sorted(training["deal_outcome"].dropna().unique().tolist()) if "deal_outcome" in training else [],
        "active_contains_outcome_column": "deal_outcome" in active.columns,
    }


def build_quality_summary(
    bronze: dict[str, pd.DataFrame],
    silver: dict[str, pd.DataFrame],
    gold: dict[str, pd.DataFrame],
) -> dict:
    """Build a combined quality summary with warnings."""

    warnings = []
    violations = competitor_column_violations({**bronze, **silver, **gold})
    if violations:
        warnings.append(f"Forbidden competitor columns found: {violations}")
    silver_summary = silver_quality_summary(silver)
    if silver_summary["active_deals_with_outcome"]:
        warnings.append("Active deals with outcomes detected")
    gold_summary = gold_quality_summary(gold)
    if gold_summary["active_contains_outcome_column"]:
        warnings.append("Active scoring dataset contains deal_outcome")

    return {
        "bronze": bronze_quality_summary(bronze),
        "silver": silver_summary,
        "gold": gold_summary,
        "warnings": warnings,
        "warning_count": len(warnings),
    }
