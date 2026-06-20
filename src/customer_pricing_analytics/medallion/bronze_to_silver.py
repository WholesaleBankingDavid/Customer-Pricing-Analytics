"""Transform source-system Bronze data into canonical Silver entities."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from customer_pricing_analytics.medallion.schemas import BRONZE_TABLES, SILVER_TABLES, assert_no_competitor_columns


def _latest_by(df: pd.DataFrame, key: str, ts_col: str = "source_extract_ts") -> pd.DataFrame:
    return df.sort_values([key, ts_col]).drop_duplicates(key, keep="last").copy()


def _customer_id(crm_account_id: str) -> str:
    digits = re.sub(r"\D", "", str(crm_account_id))
    return f"CUST{int(digits):06d}" if digits else f"CUST-{crm_account_id}"


def _deal_id(opportunity_id: str) -> str:
    digits = re.sub(r"\D", "", str(opportunity_id))
    return f"DEAL{int(digits):07d}" if digits else f"DEAL-{opportunity_id}"


def _facility_id(facility_source_id: str) -> str:
    digits = re.sub(r"\D", "", str(facility_source_id))
    return f"FAC{int(digits):08d}" if digits else f"FAC-{facility_source_id}"


def _standardize_segment(value) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"large corp", "large corporate", "lc"}:
        return "Large Corporate"
    if normalized in {"mid market", "mm"}:
        return "Mid Market"
    if "sponsor" in normalized:
        return "Financial Sponsor"
    return str(value).strip().title()


def _standardize_currency(value) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().upper()
    if normalized in {"€", "EUR"}:
        return "EUR"
    return normalized


def _standardize_stage(value) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"closed won", "closed lost", "withdrawn"}:
        return normalized.replace(" ", "_")
    return "active"


def _deal_outcome(stage_raw) -> str | None:
    stage = str(stage_raw).strip().lower()
    if stage == "closed won":
        return "won"
    if stage == "closed lost":
        return "lost"
    return None


def _standardize_lost_reason(value) -> str | None:
    if pd.isna(value) or value is None:
        return None
    normalized = str(value).strip().lower()
    if "price" in normalized or "expensive" in normalized:
        return "price"
    if "alternative" in normalized:
        return "alternative_funding"
    if "cancel" in normalized:
        return "project_cancelled"
    if "credit" in normalized:
        return "credit_declined"
    if "structure" in normalized:
        return "structure"
    if "no longer" in normalized:
        return "no_longer_needed"
    return normalized.replace(" ", "_")


def _commercial_relevance(lost_reason: str | None, deal_outcome: str | None, status: str) -> bool:
    if status == "active" or deal_outcome == "won":
        return True
    if lost_reason in {"price", "alternative_funding", "structure", "relationship"}:
        return True
    if lost_reason in {"credit_declined", "project_cancelled", "no_longer_needed"}:
        return False
    return True


def _parse_utilization(value, product_type: str | None = None) -> float:
    if pd.isna(value):
        value = None
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"", "n/a", "na", "none"}:
            value = None
        elif cleaned.endswith("%"):
            return max(0.0, min(1.0, float(cleaned.rstrip("%")) / 100))
        else:
            try:
                return max(0.0, min(1.0, float(cleaned)))
            except ValueError:
                value = None
    if value is not None:
        return max(0.0, min(1.0, float(value)))
    defaults = {
        "RCF": 0.45,
        "Term Loan": 1.0,
        "Guarantee": 0.20,
        "Trade Finance": 0.25,
        "Overdraft": 0.35,
    }
    return defaults.get(product_type or "", 0.50)


def _standardize_product(value) -> str:
    normalized = str(value).strip().lower()
    if "term" in normalized:
        return "Term Loan"
    if "guarantee" in normalized or "guarant" in normalized:
        return "Guarantee"
    if "trade" in normalized:
        return "Trade Finance"
    if "overdraft" in normalized:
        return "Overdraft"
    return "RCF" if "rcf" in normalized or "revolving" in normalized else str(value).strip()


def _standardize_rating(value) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    mapping = {
        "a": "A",
        "a2": "A",
        "bbb": "BBB",
        "baa2": "BBB",
        "bb": "BB",
        "ba2": "BB",
        "b": "B",
        "b2": "B",
    }
    return mapping.get(normalized, str(value).strip().upper())


def _to_number(value) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, str) and value.strip().endswith("%"):
        return float(value.strip().rstrip("%")) / 100
    return float(value)


def transform_bronze_to_silver(bronze_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build canonical Silver entities from Bronze tables."""

    accounts = _latest_by(bronze_tables[BRONZE_TABLES["crm_accounts"]], "crm_account_id")
    customers = pd.DataFrame(
        {
            "customer_id": accounts["crm_account_id"].map(_customer_id),
            "crm_account_id": accounts["crm_account_id"],
            "customer_segment": accounts["customer_segment_raw"].map(_standardize_segment),
            "industry": accounts["industry_raw"].astype("string"),
            "region": accounts["region_raw"].replace({"West Europe": "Western Europe"}),
            "country": accounts["country_raw"].astype("string").str.upper(),
            "group_id": accounts["group_ref"],
            "rm_id": accounts["rm_owner_code"],
            "onboarding_date": pd.to_datetime(accounts["onboarding_date"], errors="coerce"),
            "relationship_status": accounts["relationship_status_raw"].astype("string").str.lower(),
            "annual_revenue_bucket": accounts["annual_revenue_bucket_raw"],
            "employee_count_bucket": accounts["employee_count_bucket_raw"],
            "is_active_customer": accounts["relationship_status_raw"].astype(str).str.lower().isin(["active"]),
        }
    )

    opportunities = bronze_tables[BRONZE_TABLES["crm_opportunities"]].copy()
    applications = _latest_by(bronze_tables[BRONZE_TABLES["los_applications"]], "application_id")
    deals = opportunities.merge(
        applications[["application_id", "opportunity_id", "financing_purpose_raw", "submission_date", "approval_date", "decline_date"]],
        on="opportunity_id",
        how="left",
    )
    deals["deal_status"] = deals["stage_raw"].map(_standardize_stage)
    deals["deal_outcome"] = deals["stage_raw"].map(_deal_outcome)
    deals.loc[deals["deal_status"].eq("active"), "deal_outcome"] = None
    deals["lost_reason"] = deals["lost_reason_raw"].map(_standardize_lost_reason)
    deals["commercial_relevance_flag"] = [
        _commercial_relevance(reason, outcome, status)
        for reason, outcome, status in zip(deals["lost_reason"], deals["deal_outcome"], deals["deal_status"])
    ]
    silver_deals = pd.DataFrame(
        {
            "deal_id": deals["opportunity_id"].map(_deal_id),
            "opportunity_id": deals["opportunity_id"],
            "application_id": deals["application_id"],
            "customer_id": deals["crm_account_id"].map(_customer_id),
            "deal_type": deals["opportunity_type_raw"],
            "financing_purpose": deals["financing_purpose_raw"],
            "deal_status": deals["deal_status"],
            "offer_date": pd.to_datetime(deals["submission_date"], errors="coerce").fillna(pd.to_datetime(deals["created_date"], errors="coerce")),
            "expected_close_date": pd.to_datetime(deals["expected_close_date"], errors="coerce"),
            "decision_date": pd.to_datetime(deals["actual_close_date"], errors="coerce"),
            "deal_outcome": deals["deal_outcome"],
            "lost_reason": deals["lost_reason"],
            "commercial_relevance_flag": deals["commercial_relevance_flag"],
            "rm_id": deals["owner_rm_code"],
            "current_stage": deals["stage_raw"],
        }
    )

    raw_facilities = _latest_by(bronze_tables[BRONZE_TABLES["los_facilities"]], "facility_source_id")
    facilities = raw_facilities.merge(
        silver_deals[["deal_id", "application_id"]],
        on="application_id",
        how="inner",
    )
    facilities["product_type"] = facilities["product_type_raw"].map(_standardize_product)
    facilities["expected_utilization"] = [
        _parse_utilization(value, product)
        for value, product in zip(facilities["expected_utilisation_raw"], facilities["product_type"])
    ]
    silver_facilities = pd.DataFrame(
        {
            "facility_id": facilities["facility_source_id"].map(_facility_id),
            "facility_source_id": facilities["facility_source_id"],
            "deal_id": facilities["deal_id"],
            "application_id": facilities["application_id"],
            "product_type": facilities["product_type"],
            "commitment_amount": pd.to_numeric(facilities["commitment_amount"], errors="coerce"),
            "drawn_amount_initial": pd.to_numeric(facilities["drawn_amount_initial"], errors="coerce"),
            "expected_utilization": facilities["expected_utilization"],
            "expected_utilized_volume": pd.to_numeric(facilities["commitment_amount"], errors="coerce") * facilities["expected_utilization"],
            "currency": facilities["currency"].map(_standardize_currency),
            "tenor_months": pd.to_numeric(facilities["tenor_months"], errors="coerce"),
            "maturity_date": pd.to_datetime(facilities["maturity_date"], errors="coerce"),
            "repayment_type": facilities["repayment_type_raw"].astype("string").str.title(),
            "interest_type": facilities["interest_type_raw"].replace({"floater": "Floating"}),
            "collateral_type": facilities["collateral_type_raw"],
            "covenant_package": facilities["covenant_package_raw"],
        }
    )

    quotes = bronze_tables[BRONZE_TABLES["pricing_quotes"]].copy()
    quotes = quotes.merge(
        silver_facilities[["facility_id", "facility_source_id", "deal_id"]],
        on="facility_source_id",
        how="inner",
    )
    quotes["quote_status"] = quotes["quote_status_raw"].astype("string").str.lower()
    eligible = quotes["quote_status"].isin(["approved", "submitted"])
    eligible_latest = quotes[eligible].sort_values(["facility_id", "quote_version"]).groupby("facility_id").tail(1)
    fallback_latest = quotes.sort_values(["facility_id", "quote_version"]).groupby("facility_id").tail(1)
    final_ids = dict(zip(fallback_latest["facility_id"], fallback_latest["quote_id"]))
    final_ids.update(dict(zip(eligible_latest["facility_id"], eligible_latest["quote_id"])))
    quotes["is_final_quote"] = quotes["quote_id"].eq(quotes["facility_id"].map(final_ids))
    silver_pricing = pd.DataFrame(
        {
            "pricing_case_id": "PC-" + quotes["quote_id"].astype(str),
            "deal_id": quotes["deal_id"],
            "facility_id": quotes["facility_id"],
            "quote_id": quotes["quote_id"],
            "quote_version": pd.to_numeric(quotes["quote_version"], errors="coerce"),
            "is_final_quote": quotes["is_final_quote"],
            "quote_status": quotes["quote_status"],
            "quote_created_at": pd.to_datetime(quotes["quote_created_at"], errors="coerce"),
            "offered_margin_bps": pd.to_numeric(quotes["offered_margin_bps"], errors="coerce"),
            "upfront_fee_bps": pd.to_numeric(quotes["upfront_fee_bps"], errors="coerce").fillna(0),
            "commitment_fee_bps": pd.to_numeric(quotes["commitment_fee_bps"], errors="coerce").fillna(0),
            "utilisation_fee_bps": pd.to_numeric(quotes["utilisation_fee_bps"], errors="coerce").fillna(0),
            "arrangement_fee_bps": pd.to_numeric(quotes["arrangement_fee_bps"], errors="coerce").fillna(0),
            "floor_margin_bps": pd.to_numeric(quotes["floor_margin_bps"], errors="coerce"),
            "target_margin_bps": pd.to_numeric(quotes["target_margin_bps"], errors="coerce"),
            "stretch_margin_bps": pd.to_numeric(quotes["stretch_margin_bps"], errors="coerce"),
            "margin_above_floor_bps": pd.to_numeric(quotes["offered_margin_bps"], errors="coerce") - pd.to_numeric(quotes["floor_margin_bps"], errors="coerce"),
            "rm_override_flag": quotes["rm_override_flag"].astype(bool),
            "override_reason": quotes["override_reason_raw"],
            "approval_status": quotes["approval_status_raw"].astype("string").str.lower(),
            "final_quote_warning": quotes["is_final_quote"] & ~quotes["quote_status"].isin(["approved", "submitted"]),
        }
    )

    raw_risk = bronze_tables[BRONZE_TABLES["risk_assessments"]].copy()
    raw_risk = raw_risk.merge(
        silver_facilities[["facility_id", "facility_source_id", "deal_id"]],
        on="facility_source_id",
        how="inner",
    )
    raw_risk["assessment_date"] = pd.to_datetime(raw_risk["assessment_date"], errors="coerce")
    raw_risk = raw_risk.sort_values(["facility_id", "assessment_date", "source_extract_ts"]).groupby("facility_id").tail(1)
    silver_risk = pd.DataFrame(
        {
            "risk_assessment_id": raw_risk["risk_assessment_id"],
            "deal_id": raw_risk["deal_id"],
            "facility_id": raw_risk["facility_id"],
            "rating": raw_risk["rating_raw"].map(_standardize_rating),
            "pd": raw_risk["pd_raw"].map(_to_number),
            "lgd": raw_risk["lgd_raw"].map(_to_number),
            "ead": pd.to_numeric(raw_risk["ead_amount"], errors="coerce"),
            "rwa": pd.to_numeric(raw_risk["rwa_amount"], errors="coerce"),
            "expected_loss": pd.to_numeric(raw_risk["expected_loss_amount"], errors="coerce"),
            "risk_model_version": raw_risk["risk_model_version"],
            "assessment_date": raw_risk["assessment_date"],
            "watchlist_flag": raw_risk["watchlist_flag"].astype(bool),
        }
    )

    snapshots = bronze_tables[BRONZE_TABLES["core_relationship_snapshot"]].copy()
    snapshots["customer_id"] = snapshots["crm_account_id"].map(_customer_id)
    snapshots["snapshot_month"] = pd.to_datetime(snapshots["snapshot_month"], errors="coerce")
    revenue_rank = snapshots["relationship_revenue_ltm"].rank(pct=True)
    products_rank = snapshots["existing_product_count"].rank(pct=True)
    recency_rank = 1 - snapshots["days_since_last_contact"].rank(pct=True)
    snapshots["relationship_strength_score"] = (0.40 * revenue_rank + 0.35 * products_rank + 0.25 * recency_rank).clip(0, 1)
    silver_relationship = snapshots[
        [
            "customer_id",
            "snapshot_month",
            "total_existing_exposure",
            "total_drawn_amount",
            "deposit_balance_avg",
            "existing_product_count",
            "relationship_revenue_ltm",
            "relationship_cost_ltm",
            "relationship_margin_ltm",
            "days_since_last_contact",
            "relationship_strength_score",
        ]
    ].copy()

    ftp = bronze_tables[BRONZE_TABLES["treasury_ftp_rates"]].copy()
    ftp["currency"] = ftp["currency"].map(_standardize_currency)
    ftp["product_group"] = ftp["product_group_raw"]
    silver_ftp = ftp[
        [
            "ftp_curve_date",
            "currency",
            "product_group",
            "tenor_bucket_months",
            "ftp_bps",
            "liquidity_cost_bps",
        ]
    ].copy()

    tables = {
        SILVER_TABLES["customers"]: customers.reset_index(drop=True),
        SILVER_TABLES["deals"]: silver_deals.reset_index(drop=True),
        SILVER_TABLES["facilities"]: silver_facilities.reset_index(drop=True),
        SILVER_TABLES["pricing_cases"]: silver_pricing.reset_index(drop=True),
        SILVER_TABLES["risk_assessments"]: silver_risk.reset_index(drop=True),
        SILVER_TABLES["relationship_snapshots"]: silver_relationship.reset_index(drop=True),
        SILVER_TABLES["ftp_rates"]: silver_ftp.reset_index(drop=True),
    }
    assert_no_competitor_columns(tables)
    return tables
