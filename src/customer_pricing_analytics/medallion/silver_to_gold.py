"""Build Gold analytical marts from Silver canonical entities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from customer_pricing_analytics.medallion.schemas import GOLD_TABLES, SILVER_TABLES, assert_no_competitor_columns
from customer_pricing_analytics.pricing_economics import (
    assign_pricing_zone,
    calculate_expected_facility_profit,
    calculate_risk_adjusted_margin_bps,
)


ZONE_ORDER = {"Red": 0, "Guardrail": 1, "Recommended": 2, "Stretch": 3}


def _product_group(product_type: str) -> str:
    if product_type in {"RCF", "Overdraft"}:
        return "Committed Lines"
    if product_type == "Term Loan":
        return "Term Lending"
    if product_type == "Guarantee":
        return "Guarantee"
    return "Trade"


def _tenor_bucket(tenor_months: float) -> int:
    buckets = np.array([12, 24, 36, 60, 84])
    if pd.isna(tenor_months):
        return 36
    return int(buckets[np.abs(buckets - float(tenor_months)).argmin()])


def _latest_relationship(silver_relationship: pd.DataFrame) -> pd.DataFrame:
    return (
        silver_relationship.sort_values(["customer_id", "snapshot_month"])
        .groupby("customer_id")
        .tail(1)
        .copy()
    )


def _annualized_fee_bps(row: pd.Series) -> float:
    tenor_years = max(float(row.get("tenor_years", 1) or 1), 0.25)
    upfront = float(row.get("upfront_fee_bps", 0) or 0) / tenor_years
    arrangement = float(row.get("arrangement_fee_bps", 0) or 0) / tenor_years
    commitment = float(row.get("commitment_fee_bps", 0) or 0)
    utilisation = float(row.get("utilisation_fee_bps", 0) or 0)
    utilization = float(row.get("expected_utilization", 0) or 0)
    product_type = row.get("product_type")
    if product_type in {"RCF", "Overdraft"}:
        return upfront + arrangement + commitment * (1 - utilization) + utilisation * utilization
    if product_type in {"Guarantee", "Trade Finance"}:
        return upfront + arrangement + utilisation
    return upfront + arrangement


def _worst_zone(zones: pd.Series) -> str:
    if zones.empty:
        return "Red"
    return min(zones, key=lambda zone: ZONE_ORDER.get(zone, 99))


def _deal_pricing_zone(row: pd.Series) -> str:
    if row["total_expected_profit_lifetime"] < 0:
        return "Red"
    return row["worst_facility_pricing_zone"]


def _fee_share(group: pd.DataFrame) -> float:
    fee = group["annualized_fee_bps"].fillna(0).sum()
    margin = group["offered_margin_bps"].fillna(0).sum()
    total = fee + margin
    return float(fee / total) if total else 0.0


def _risk_cost_bps(expected_loss: float, expected_utilized_volume: float, tenor_years: float) -> float:
    denominator = max(float(expected_utilized_volume or 0) * max(float(tenor_years or 0), 0.25), 1.0)
    return float(expected_loss or 0) / denominator * 10000


def _build_facility_economics(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    facilities = silver[SILVER_TABLES["facilities"]]
    pricing = silver[SILVER_TABLES["pricing_cases"]]
    risk = silver[SILVER_TABLES["risk_assessments"]]
    ftp = silver[SILVER_TABLES["ftp_rates"]]

    final_pricing = pricing[pricing["is_final_quote"]].copy()
    df = facilities.merge(final_pricing, on=["deal_id", "facility_id"], how="inner")
    df = df.merge(risk, on=["deal_id", "facility_id"], how="left")
    df["tenor_years"] = df["tenor_months"] / 12
    df["product_group"] = df["product_type"].map(_product_group)
    df["tenor_bucket_months"] = df["tenor_months"].map(_tenor_bucket)

    latest_ftp = (
        ftp.sort_values("ftp_curve_date")
        .groupby(["currency", "product_group", "tenor_bucket_months"])
        .tail(1)
    )
    df = df.merge(
        latest_ftp[["currency", "product_group", "tenor_bucket_months", "ftp_bps", "liquidity_cost_bps"]],
        on=["currency", "product_group", "tenor_bucket_months"],
        how="left",
    )
    df["ftp_bps"] = df["ftp_bps"].fillna(110)
    df["liquidity_cost_bps"] = df["liquidity_cost_bps"].fillna(20)
    df["annualized_fee_bps"] = df.apply(_annualized_fee_bps, axis=1)
    df["risk_cost_bps"] = [
        _risk_cost_bps(loss, volume, tenor)
        for loss, volume, tenor in zip(df["expected_loss"].fillna(0), df["expected_utilized_volume"].fillna(0), df["tenor_years"].fillna(1))
    ]
    df["admin_cost_bps"] = np.where(df["product_type"].isin(["Guarantee", "Trade Finance"]), 12.0, 8.0)
    df["capital_cost_bps"] = ((df["rwa"].fillna(0) / df["ead"].replace(0, np.nan).fillna(df["expected_utilized_volume"].replace(0, np.nan))).fillna(0.75) * 18).clip(8, 35)
    df["risk_adjusted_margin_bps"] = [
        calculate_risk_adjusted_margin_bps(
            offered_margin_bps=offered,
            annualized_fee_bps=fee,
            ftp_bps=ftp_bps,
            liquidity_cost_bps=liquidity,
            risk_cost_bps=risk_cost,
            admin_cost_bps=admin,
            capital_cost_bps=capital,
        )
        for offered, fee, ftp_bps, liquidity, risk_cost, admin, capital in zip(
            df["offered_margin_bps"],
            df["annualized_fee_bps"],
            df["ftp_bps"],
            df["liquidity_cost_bps"],
            df["risk_cost_bps"],
            df["admin_cost_bps"],
            df["capital_cost_bps"],
        )
    ]
    df["expected_facility_profit_annual"] = [
        calculate_expected_facility_profit(margin, volume, 1.0)
        for margin, volume in zip(df["risk_adjusted_margin_bps"], df["expected_utilized_volume"])
    ]
    df["expected_facility_profit_lifetime"] = [
        calculate_expected_facility_profit(margin, volume, tenor)
        for margin, volume, tenor in zip(df["risk_adjusted_margin_bps"], df["expected_utilized_volume"], df["tenor_years"])
    ]
    df["pricing_zone"] = [
        assign_pricing_zone(offered, floor, target, stretch, risk_adjusted)
        for offered, floor, target, stretch, risk_adjusted in zip(
            df["offered_margin_bps"],
            df["floor_margin_bps"],
            df["target_margin_bps"],
            df["stretch_margin_bps"],
            df["risk_adjusted_margin_bps"],
        )
    ]
    return df[
        [
            "deal_id",
            "facility_id",
            "product_type",
            "commitment_amount",
            "expected_utilization",
            "expected_utilized_volume",
            "tenor_months",
            "tenor_years",
            "offered_margin_bps",
            "annualized_fee_bps",
            "ftp_bps",
            "liquidity_cost_bps",
            "risk_cost_bps",
            "admin_cost_bps",
            "capital_cost_bps",
            "floor_margin_bps",
            "target_margin_bps",
            "stretch_margin_bps",
            "margin_above_floor_bps",
            "risk_adjusted_margin_bps",
            "expected_facility_profit_annual",
            "expected_facility_profit_lifetime",
            "pricing_zone",
        ]
    ].copy()


def _build_deal_economics(facility_economics: pd.DataFrame, silver_deals: pd.DataFrame) -> pd.DataFrame:
    grouped = facility_economics.groupby("deal_id")
    base = grouped.agg(
        anchor_product=("product_type", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
        number_of_facilities=("facility_id", "nunique"),
        total_commitment=("commitment_amount", "sum"),
        total_expected_utilized_volume=("expected_utilized_volume", "sum"),
        total_expected_profit_annual=("expected_facility_profit_annual", "sum"),
        total_expected_profit_lifetime=("expected_facility_profit_lifetime", "sum"),
        weighted_avg_margin_above_floor_bps=("margin_above_floor_bps", "mean"),
        min_margin_above_floor_bps=("margin_above_floor_bps", "min"),
        worst_facility_pricing_zone=("pricing_zone", _worst_zone),
    )
    base["fee_income_share"] = grouped.apply(_fee_share)
    product_flags = pd.get_dummies(facility_economics.set_index("deal_id")["product_type"]).groupby("deal_id").max()
    for column, output in [
        ("RCF", "has_rcf"),
        ("Term Loan", "has_term_loan"),
        ("Guarantee", "has_guarantee"),
        ("Trade Finance", "has_trade_finance"),
    ]:
        base[output] = product_flags[column].astype(bool) if column in product_flags else False
    base["deal_complexity_score"] = (
        base["number_of_facilities"].rank(pct=True) * 0.65
        + base["total_commitment"].rank(pct=True) * 0.35
    ).clip(0, 1)
    base["deal_pricing_zone"] = base.apply(_deal_pricing_zone, axis=1)
    deal_reference = silver_deals[["deal_id", "customer_id", "rm_id"]].drop_duplicates("deal_id")
    return deal_reference.merge(base.reset_index(), on="deal_id", how="inner")


def _risk_by_deal(risk: pd.DataFrame, facility_economics: pd.DataFrame) -> pd.DataFrame:
    weights = facility_economics[["deal_id", "facility_id", "expected_utilized_volume"]]
    df = risk.merge(weights, on=["deal_id", "facility_id"], how="left")
    def weighted(series, group):
        w = group["expected_utilized_volume"].fillna(0)
        if w.sum() == 0:
            return series.mean()
        return np.average(series.fillna(series.mean()), weights=w)
    rows = []
    for deal_id, group in df.groupby("deal_id"):
        rows.append(
            {
                "deal_id": deal_id,
                "rating_at_offer": group["rating"].mode().iloc[0] if not group["rating"].mode().empty else None,
                "pd_at_offer": weighted(group["pd"], group),
                "lgd_weighted": weighted(group["lgd"], group),
            }
        )
    return pd.DataFrame(rows)


def _training_features(
    silver: dict[str, pd.DataFrame],
    deal_economics: pd.DataFrame,
    facility_economics: pd.DataFrame,
) -> pd.DataFrame:
    deals = silver[SILVER_TABLES["deals"]]
    customers = silver[SILVER_TABLES["customers"]]
    relationship = _latest_relationship(silver[SILVER_TABLES["relationship_snapshots"]])
    risk = _risk_by_deal(silver[SILVER_TABLES["risk_assessments"]], facility_economics)

    base = deals.merge(customers[["customer_id", "customer_segment", "industry", "region"]], on="customer_id", how="left")
    base = base.merge(relationship[["customer_id", "relationship_strength_score", "existing_product_count", "days_since_last_contact"]], on="customer_id", how="left")
    base = base.merge(deal_economics, on=["deal_id", "customer_id", "rm_id"], how="inner")
    base = base.merge(risk, on="deal_id", how="left")
    return base


def transform_silver_to_gold(silver_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Create Gold facility, deal, training, scoring, and dashboard marts."""

    facility_economics = _build_facility_economics(silver_tables)
    deals = silver_tables[SILVER_TABLES["deals"]]
    deal_economics = _build_deal_economics(facility_economics, deals)
    features = _training_features(silver_tables, deal_economics, facility_economics)

    feature_cols = [
        "deal_id",
        "customer_id",
        "rm_id",
        "customer_segment",
        "industry",
        "region",
        "rating_at_offer",
        "pd_at_offer",
        "lgd_weighted",
        "relationship_strength_score",
        "existing_product_count",
        "days_since_last_contact",
        "anchor_product",
        "number_of_facilities",
        "total_commitment",
        "total_expected_utilized_volume",
        "weighted_avg_margin_above_floor_bps",
        "min_margin_above_floor_bps",
        "total_expected_profit_annual",
        "total_expected_profit_lifetime",
        "fee_income_share",
        "deal_complexity_score",
        "has_rcf",
        "has_term_loan",
        "has_guarantee",
        "has_trade_finance",
    ]
    training = features[
        features["deal_status"].isin(["closed_won", "closed_lost"])
        & features["commercial_relevance_flag"].eq(True)
        & features["deal_outcome"].isin(["won", "lost"])
    ][feature_cols + ["deal_outcome"]].copy()

    active = features[features["deal_status"].eq("active")].copy()
    active_scoring = active[feature_cols + ["expected_close_date", "current_stage", "deal_pricing_zone", "total_expected_profit_annual", "total_expected_profit_lifetime"]].copy()
    active_scoring = active_scoring.rename(columns={"deal_pricing_zone": "pricing_zone"})
    active_scoring = active_scoring.loc[:, ~active_scoring.columns.duplicated()]

    dashboard = active[
        [
            "deal_id",
            "customer_id",
            "rm_id",
            "customer_segment",
            "industry",
            "anchor_product",
            "total_commitment",
            "number_of_facilities",
            "current_stage",
            "expected_close_date",
            "relationship_strength_score",
            "deal_pricing_zone",
            "min_margin_above_floor_bps",
            "total_expected_profit_annual",
            "total_expected_profit_lifetime",
        ]
    ].rename(columns={"deal_pricing_zone": "pricing_zone"})
    dashboard["recommended_action_placeholder"] = np.select(
        [
            dashboard["pricing_zone"].eq("Red"),
            dashboard["pricing_zone"].eq("Guardrail"),
            dashboard["relationship_strength_score"].fillna(0) > 0.7,
        ],
        [
            "Review economics and guardrail exception",
            "Prepare pricing justification",
            "Prioritize RM follow-up",
        ],
        default="Monitor pipeline",
    )
    dashboard["data_quality_warning_flag"] = dashboard[["relationship_strength_score", "min_margin_above_floor_bps"]].isna().any(axis=1)

    tables = {
        GOLD_TABLES["facility_economics"]: facility_economics.reset_index(drop=True),
        GOLD_TABLES["deal_economics"]: deal_economics.reset_index(drop=True),
        GOLD_TABLES["deal_training_dataset"]: training.reset_index(drop=True),
        GOLD_TABLES["active_deal_scoring_dataset"]: active_scoring.reset_index(drop=True),
        GOLD_TABLES["rm_deal_dashboard"]: dashboard.reset_index(drop=True),
    }
    assert_no_competitor_columns(tables)
    return tables
