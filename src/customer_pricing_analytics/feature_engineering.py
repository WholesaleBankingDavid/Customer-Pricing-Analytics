"""Feature engineering for facility and deal-level pricing analytics."""

import numpy as np
import pandas as pd


def create_margin_above_floor(df: pd.DataFrame) -> pd.DataFrame:
    """Add margin_above_floor_bps from offered and floor margins when available."""

    result = df.copy()
    required = {"offered_margin_bps", "floor_margin_bps"}
    if required.issubset(result.columns):
        result["margin_above_floor_bps"] = (
            result["offered_margin_bps"] - result["floor_margin_bps"]
        )
    return result


def create_tenor_years(df: pd.DataFrame) -> pd.DataFrame:
    """Add tenor_years from tenor_months when available."""

    result = df.copy()
    if "tenor_months" in result.columns:
        result["tenor_years"] = result["tenor_months"] / 12
    return result


def create_expected_utilized_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Add expected_utilized_volume from commitment and expected utilization."""

    result = df.copy()
    required = {"commitment_amount", "expected_utilization"}
    if required.issubset(result.columns):
        result["expected_utilized_volume"] = (
            result["commitment_amount"] * result["expected_utilization"]
        )
    return result


def _weighted_average(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna()
    if not valid.any() or weights[valid].sum() == 0:
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


def create_deal_level_features(facility_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate facility-level features to deal level."""

    if "deal_id" not in facility_df.columns:
        raise ValueError("facility_df must contain deal_id")

    df = create_expected_utilized_volume(create_margin_above_floor(facility_df))

    if "expected_utilized_volume" not in df.columns:
        df["expected_utilized_volume"] = 0.0
    if "commitment_amount" not in df.columns:
        df["commitment_amount"] = 0.0
    if "margin_above_floor_bps" not in df.columns:
        df["margin_above_floor_bps"] = np.nan

    grouped = df.groupby("deal_id", dropna=False)
    result = grouped.agg(
        number_of_facilities=("deal_id", "size"),
        total_commitment=("commitment_amount", "sum"),
        total_expected_utilized_volume=("expected_utilized_volume", "sum"),
        min_margin_above_floor_bps=("margin_above_floor_bps", "min"),
    )

    result["weighted_avg_margin_above_floor_bps"] = grouped.apply(
        lambda group: _weighted_average(
            group["margin_above_floor_bps"],
            group["expected_utilized_volume"].fillna(0),
        ),
        include_groups=False,
    )

    if "upfront_fee_bps" in df.columns and "offered_margin_bps" in df.columns:
        fee = grouped["upfront_fee_bps"].sum()
        margin = grouped["offered_margin_bps"].sum().replace(0, np.nan)
        result["fee_share"] = (fee / (fee + margin)).fillna(0)
    else:
        result["fee_share"] = 0.0

    product = df.get("product_type", pd.Series("", index=df.index)).astype(str).str.lower()
    product_flags = pd.DataFrame({"deal_id": df["deal_id"], "product_type": product})
    flags = product_flags.groupby("deal_id")["product_type"].agg(
        has_rcf=lambda values: values.str.contains("rcf|revolving|revolver", regex=True).any(),
        has_term_loan=lambda values: values.str.contains("term", regex=True).any(),
        has_guarantee=lambda values: values.str.contains("guarantee|guarant", regex=True).any(),
    )

    return result.join(flags).reset_index()
