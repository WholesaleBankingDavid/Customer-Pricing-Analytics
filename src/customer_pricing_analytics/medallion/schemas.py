"""Table names and schema helpers for the medallion demo pipeline."""

BRONZE_TABLES = {
    "crm_accounts": "bronze_crm_accounts",
    "crm_opportunities": "bronze_crm_opportunities",
    "los_applications": "bronze_los_applications",
    "los_facilities": "bronze_los_facilities",
    "pricing_quotes": "bronze_pricing_quotes",
    "risk_assessments": "bronze_risk_assessments",
    "treasury_ftp_rates": "bronze_treasury_ftp_rates",
    "core_relationship_snapshot": "bronze_core_relationship_snapshot",
    "rm_activities": "bronze_rm_activities",
}

SILVER_TABLES = {
    "customers": "silver_customers",
    "deals": "silver_deals",
    "facilities": "silver_facilities",
    "pricing_cases": "silver_pricing_cases",
    "risk_assessments": "silver_risk_assessments",
    "relationship_snapshots": "silver_relationship_snapshots",
    "ftp_rates": "silver_ftp_rates",
}

GOLD_TABLES = {
    "facility_economics": "gold_facility_economics",
    "deal_economics": "gold_deal_economics",
    "deal_training_dataset": "gold_deal_training_dataset",
    "active_deal_scoring_dataset": "gold_active_deal_scoring_dataset",
    "rm_deal_dashboard": "gold_rm_deal_dashboard",
}

FORBIDDEN_COMPETITOR_TERMS = ("competitor", "competition", "competing_bank")


def assert_no_competitor_columns(tables: dict) -> None:
    """Raise if generated tables contain competitor-style column names."""

    offenders: list[str] = []
    for table_name, df in tables.items():
        for column in df.columns:
            normalized = column.lower()
            if any(term in normalized for term in FORBIDDEN_COMPETITOR_TERMS):
                offenders.append(f"{table_name}.{column}")
    if offenders:
        raise ValueError(f"Forbidden competitor columns found: {offenders}")
