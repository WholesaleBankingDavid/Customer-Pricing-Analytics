"""Generate realistic synthetic Bronze source-system tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from customer_pricing_analytics.medallion.schemas import BRONZE_TABLES, assert_no_competitor_columns


@dataclass(frozen=True)
class BronzeGenerationConfig:
    n_customers: int = 500
    n_opportunities: int = 1500
    active_share: float = 0.25
    random_state: int = 42


def _rng(random_state: int) -> np.random.Generator:
    return np.random.default_rng(random_state)


def _choice(rng: np.random.Generator, values, size=None, p=None):
    return rng.choice(values, size=size, p=p)


def _random_dates(
    rng: np.random.Generator,
    start: str,
    end: str,
    size: int,
) -> pd.Series:
    start_ts = pd.Timestamp(start).value // 10**9
    end_ts = pd.Timestamp(end).value // 10**9
    values = rng.integers(start_ts, end_ts, size=size)
    return pd.to_datetime(values, unit="s").normalize()


def _source_ts(rng: np.random.Generator, size: int) -> pd.Series:
    return _random_dates(rng, "2025-01-01", "2025-12-31", size) + pd.to_timedelta(
        rng.integers(0, 24, size=size), unit="h"
    )


def _sigmoid(values) -> np.ndarray:
    return 1 / (1 + np.exp(-values))


def _make_accounts(config: BronzeGenerationConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = config.n_customers
    industry_roots = [
        "Manufacturing",
        "Logistics",
        "Healthcare",
        "Technology",
        "Energy",
        "Retail",
        "Infrastructure",
        "Chemicals",
    ]
    legal_suffix = _choice(rng, ["GmbH", "AG", "Ltd", "SAS", "BV"], n)
    industries = _choice(rng, industry_roots, n)
    accounts = pd.DataFrame(
        {
            "crm_account_id": [f"CRM{idx:06d}" for idx in range(1, n + 1)],
            "legal_entity_name_synthetic": [
                f"Synthetic {industry} {suffix} {idx:03d}"
                for idx, (industry, suffix) in enumerate(zip(industries, legal_suffix), start=1)
            ],
            "customer_segment_raw": _choice(
                rng,
                ["Large Corp", "Large Corporate", "LC", "Mid Market", "MM", "Financial Sponsor"],
                n,
                p=[0.25, 0.24, 0.08, 0.22, 0.12, 0.09],
            ),
            "industry_raw": industries,
            "region_raw": _choice(rng, ["DACH", "Western Europe", "Nordics", "UKI", "CEE"], n),
            "country_raw": _choice(rng, ["DE", "FR", "NL", "GB", "ES", "IT", "SE"], n),
            "group_ref": [f"GRP{idx:05d}" for idx in rng.integers(1, max(2, n // 4), n)],
            "rm_owner_code": [f"RM{idx:03d}" for idx in rng.integers(1, 80, n)],
            "onboarding_date": _random_dates(rng, "2010-01-01", "2024-06-30", n),
            "relationship_status_raw": _choice(
                rng, ["Active", "active", "Dormant", "Inactive"], n, p=[0.78, 0.12, 0.06, 0.04]
            ),
            "annual_revenue_bucket_raw": _choice(
                rng, ["<100m", "100m-500m", "500m-1bn", ">1bn", None], n, p=[0.18, 0.36, 0.25, 0.17, 0.04]
            ),
            "employee_count_bucket_raw": _choice(
                rng, ["<500", "500-2k", "2k-10k", ">10k", None], n, p=[0.20, 0.35, 0.28, 0.12, 0.05]
            ),
            "source_system": "CRM",
            "source_extract_ts": _source_ts(rng, n),
            "source_record_status": _choice(rng, ["current", "current", "current", "stale"], n),
        }
    )
    missing_regions = rng.random(n) < 0.04
    accounts.loc[missing_regions, "region_raw"] = None

    duplicate_count = max(1, int(n * 0.02))
    duplicates = accounts.sample(duplicate_count, random_state=config.random_state).copy()
    duplicates["source_extract_ts"] = duplicates["source_extract_ts"] + pd.to_timedelta(
        rng.integers(1, 20, duplicate_count), unit="D"
    )
    duplicates["source_record_status"] = "updated"
    duplicates.loc[duplicates.index[: max(1, duplicate_count // 3)], "region_raw"] = "West Europe"
    return pd.concat([accounts, duplicates], ignore_index=True)


def _make_relationship_snapshots(
    accounts: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_accounts = accounts.drop_duplicates("crm_account_id", keep="last").copy()
    months = pd.date_range("2024-07-01", periods=12, freq="MS")
    rows = []
    for account in unique_accounts.itertuples(index=False):
        product_base = int(rng.integers(1, 8))
        revenue_base = float(rng.lognormal(11.0, 0.8))
        for month in months:
            exposure = float(rng.lognormal(16.5, 0.8))
            drawn = exposure * rng.uniform(0.25, 0.9)
            revenue = revenue_base * rng.uniform(0.75, 1.25)
            cost = revenue * rng.uniform(0.25, 0.65)
            rows.append(
                {
                    "crm_account_id": account.crm_account_id,
                    "snapshot_month": month,
                    "total_existing_exposure": exposure,
                    "total_drawn_amount": drawn,
                    "deposit_balance_avg": float(rng.lognormal(15.2, 1.0)),
                    "existing_product_count": max(1, product_base + int(rng.integers(-1, 2))),
                    "relationship_revenue_ltm": revenue,
                    "relationship_cost_ltm": cost,
                    "relationship_margin_ltm": revenue - cost,
                    "days_since_last_contact": int(rng.integers(1, 180)),
                    "source_extract_ts": pd.Timestamp("2025-12-31"),
                }
            )
    snapshots = pd.DataFrame(rows)
    missing_mask = rng.random(len(snapshots)) < 0.03
    snapshots.loc[missing_mask, "deposit_balance_avg"] = np.nan

    latest = snapshots.sort_values("snapshot_month").groupby("crm_account_id").tail(1).copy()
    strength = (
        latest["existing_product_count"].rank(pct=True) * 0.35
        + latest["relationship_revenue_ltm"].rank(pct=True) * 0.35
        + (1 - latest["days_since_last_contact"].rank(pct=True)) * 0.30
    )
    latest_strength = latest[["crm_account_id"]].copy()
    latest_strength["relationship_strength_score"] = strength.clip(0, 1).to_numpy()
    return snapshots, latest_strength


def _make_opportunities(
    accounts: pd.DataFrame,
    config: BronzeGenerationConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    unique_accounts = accounts.drop_duplicates("crm_account_id", keep="last")
    n = config.n_opportunities
    created = _random_dates(rng, "2023-01-01", "2025-09-30", n)
    is_active = rng.random(n) < config.active_share
    active_stages = ["Prospecting", "Origination", "Credit Review", "Negotiation"]
    opps = pd.DataFrame(
        {
            "opportunity_id": [f"OPP{idx:07d}" for idx in range(1, n + 1)],
            "crm_account_id": _choice(rng, unique_accounts["crm_account_id"].to_numpy(), n),
            "opportunity_name_synthetic": [f"Synthetic Financing Opportunity {idx:05d}" for idx in range(1, n + 1)],
            "opportunity_type_raw": _choice(
                rng, ["New Money", "Refinancing", "Amend & Extend", "Ancillary"], n
            ),
            "stage_raw": np.where(is_active, _choice(rng, active_stages, n), "Closed Pending Simulation"),
            "expected_close_date": created + pd.to_timedelta(rng.integers(45, 240, n), unit="D"),
            "actual_close_date": pd.NaT,
            "created_date": created,
            "owner_rm_code": _choice(rng, unique_accounts["rm_owner_code"].to_numpy(), n),
            "lost_reason_raw": None,
            "pipeline_amount_raw": rng.lognormal(16.2, 0.9, n).round(2),
            "currency_raw": _choice(rng, ["EUR", "eur", "€", "USD", "GBP"], n, p=[0.62, 0.06, 0.03, 0.20, 0.09]),
            "source_last_updated_at": _source_ts(rng, n),
        }
    )
    opps["_is_active"] = is_active
    return opps


def _make_applications(opps: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    has_application = rng.random(len(opps)) < np.where(opps["_is_active"], 0.72, 0.88)
    selected = opps[has_application].copy().reset_index(drop=True)
    n = len(selected)
    submission = pd.to_datetime(selected["created_date"]) + pd.to_timedelta(rng.integers(7, 75, n), unit="D")
    apps = pd.DataFrame(
        {
            "application_id": [f"APP{idx:07d}" for idx in range(1, n + 1)],
            "opportunity_id": selected["opportunity_id"],
            "applicant_account_ref": selected["crm_account_id"],
            "application_status_raw": "Pending Simulation",
            "financing_purpose_raw": _choice(
                rng,
                ["Acquisition Finance", "Working Capital", "Capex", "Refinancing", "Trade Support"],
                n,
            ),
            "requested_amount": selected["pipeline_amount_raw"].to_numpy() * rng.uniform(0.8, 1.2, n),
            "requested_currency": selected["currency_raw"],
            "requested_tenor_months": _choice(rng, [6, 12, 24, 36, 48, 60, 84], n),
            "submission_date": submission,
            "approval_date": pd.NaT,
            "decline_date": pd.NaT,
            "credit_committee_level_raw": _choice(rng, ["Local", "Regional", "Group", None], n, p=[0.45, 0.35, 0.17, 0.03]),
            "source_extract_ts": _source_ts(rng, n),
        }
    )
    return apps


def _make_facilities(
    apps: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    account_segments = accounts.drop_duplicates("crm_account_id", keep="last").set_index("crm_account_id")[
        "customer_segment_raw"
    ]
    rows = []
    facility_idx = 1
    for app in apps.itertuples(index=False):
        segment = str(account_segments.get(app.applicant_account_ref, "Mid Market"))
        max_facilities = 4 if segment in {"Large Corp", "Large Corporate", "LC"} else 3
        n_facilities = int(_choice(rng, np.arange(1, max_facilities + 1), p=None))
        remaining = float(app.requested_amount)
        weights = rng.dirichlet(np.ones(n_facilities))
        for seq in range(1, n_facilities + 1):
            product = _choice(
                rng,
                ["RCF", "Term Loan", "Guarantee", "Trade Finance", "Overdraft"],
                p=[0.28, 0.36, 0.15, 0.14, 0.07],
            )
            commitment = max(100_000, remaining * weights[seq - 1])
            if product == "RCF":
                util = rng.uniform(0.20, 0.70)
            elif product == "Term Loan":
                util = rng.uniform(0.90, 1.0)
            elif product == "Overdraft":
                util = rng.uniform(0.15, 0.55)
            else:
                util = rng.uniform(0.05, 0.35)
            util_raw = util
            draw_style = rng.random()
            if draw_style < 0.35:
                util_raw = f"{util:.0%}"
            elif draw_style < 0.55:
                util_raw = f"{util:.2f}"
            elif draw_style < 0.60:
                util_raw = "n/a"
            tenor = int(_choice(rng, [6, 12, 24, 36, 48, 60, 84]))
            rows.append(
                {
                    "facility_source_id": f"FS{facility_idx:08d}",
                    "application_id": app.application_id,
                    "facility_sequence_no": seq,
                    "product_type_raw": product,
                    "commitment_amount": round(commitment, 2),
                    "drawn_amount_initial": round(commitment * util * rng.uniform(0.5, 1.0), 2),
                    "expected_utilisation_raw": util_raw,
                    "currency": app.requested_currency,
                    "tenor_months": tenor,
                    "maturity_date": pd.to_datetime(app.submission_date) + pd.DateOffset(months=tenor),
                    "repayment_type_raw": _choice(rng, ["Bullet", "Amortising", "Revolving", None], p=[0.42, 0.28, 0.25, 0.05]),
                    "interest_type_raw": _choice(rng, ["Floating", "Fixed", "floater"], p=[0.72, 0.20, 0.08]),
                    "collateral_type_raw": _choice(
                        rng, ["Unsecured", "Receivables", "Inventory", "Real Estate", "Cash"], p=[0.42, 0.21, 0.14, 0.18, 0.05]
                    ),
                    "covenant_package_raw": _choice(rng, ["Light", "Standard", "Tight", None], p=[0.20, 0.58, 0.17, 0.05]),
                    "source_extract_ts": _source_ts(rng, 1)[0],
                }
            )
            facility_idx += 1
    facilities = pd.DataFrame(rows)
    duplicate_count = max(1, int(len(facilities) * 0.01))
    duplicates = facilities.sample(duplicate_count, random_state=11).copy()
    duplicates["source_extract_ts"] = pd.to_datetime(duplicates["source_extract_ts"]) + pd.to_timedelta(2, unit="D")
    return pd.concat([facilities, duplicates], ignore_index=True)


def _make_pricing_quotes(facilities: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    product_floor = {
        "RCF": 115,
        "Term Loan": 130,
        "Guarantee": 80,
        "Trade Finance": 70,
        "Overdraft": 150,
    }
    rows = []
    quote_idx = 1
    for facility in facilities.drop_duplicates("facility_source_id").itertuples(index=False):
        versions = int(_choice(rng, [1, 2, 3], p=[0.25, 0.45, 0.30]))
        product = str(facility.product_type_raw)
        floor = product_floor.get(product, 120) + rng.normal(0, 8)
        target = floor + rng.uniform(25, 70)
        stretch = target + rng.uniform(35, 85)
        for version in range(1, versions + 1):
            discount = (version - 1) * rng.uniform(3, 18)
            offered = target + rng.normal(5, 22) - discount
            if rng.random() < 0.035:
                offered = floor - rng.uniform(1, 18)
            status = _choice(
                rng,
                ["Draft", "Submitted", "Approved", "Rejected"],
                p=[0.35, 0.30, 0.28, 0.07],
            )
            if version == versions and status in {"Draft", "Rejected"} and rng.random() < 0.70:
                status = _choice(rng, ["Submitted", "Approved"], p=[0.45, 0.55])
            rows.append(
                {
                    "quote_id": f"Q{quote_idx:09d}",
                    "application_id": facility.application_id,
                    "facility_source_id": facility.facility_source_id,
                    "quote_version": version,
                    "quote_status_raw": status,
                    "quote_created_at": pd.to_datetime(facility.source_extract_ts) - pd.to_timedelta((versions - version) * 5, unit="D"),
                    "offered_margin_bps": round(float(offered), 2),
                    "upfront_fee_bps": round(float(max(0, rng.normal(20, 12))), 2),
                    "commitment_fee_bps": round(float(max(0, rng.normal(35, 16))), 2) if product == "RCF" else np.nan,
                    "utilisation_fee_bps": round(float(max(0, rng.normal(15, 8))), 2) if product in {"Trade Finance", "Guarantee"} else np.nan,
                    "arrangement_fee_bps": round(float(max(0, rng.normal(18, 10))), 2),
                    "floor_margin_bps": round(float(floor), 2),
                    "target_margin_bps": round(float(target), 2),
                    "stretch_margin_bps": round(float(stretch), 2),
                    "rm_override_flag": bool(rng.random() < 0.08),
                    "override_reason_raw": _choice(rng, ["relationship", "strategic deal", "ancillary revenue", None], p=[0.25, 0.20, 0.15, 0.40]),
                    "approval_status_raw": _choice(rng, ["Approved", "Pending", "Rejected", None], p=[0.42, 0.42, 0.06, 0.10]),
                    "pricing_user_role_raw": _choice(rng, ["RM", "Pricing Desk", "Portfolio Manager"], p=[0.48, 0.42, 0.10]),
                    "source_extract_ts": _source_ts(rng, 1)[0],
                }
            )
            quote_idx += 1
    quotes = pd.DataFrame(rows)
    fee_missing = rng.random(len(quotes)) < 0.04
    quotes.loc[fee_missing, "arrangement_fee_bps"] = np.nan
    return quotes


def _make_risk_assessments(facilities: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rating_pd = {"A": 0.003, "BBB": 0.008, "BB": 0.025, "B": 0.055}
    rating_variants = {"A": ["A", "A2", "a"], "BBB": ["BBB", "Baa2", "bbb"], "BB": ["BB", "Ba2", "bb"], "B": ["B", "B2", "b"]}
    lgd_collateral = {"Cash": 0.18, "Real Estate": 0.28, "Receivables": 0.38, "Inventory": 0.45, "Unsecured": 0.55}
    rows = []
    idx = 1
    for facility in facilities.drop_duplicates("facility_source_id").itertuples(index=False):
        snapshots = int(_choice(rng, [1, 2], p=[0.70, 0.30]))
        base_rating = _choice(rng, ["A", "BBB", "BB", "B"], p=[0.18, 0.50, 0.24, 0.08])
        for snap in range(snapshots):
            pd_value = max(0.0005, rating_pd[base_rating] * rng.uniform(0.65, 1.45))
            lgd_value = max(0.05, min(0.85, lgd_collateral.get(facility.collateral_type_raw, 0.50) * rng.uniform(0.85, 1.20)))
            ead = float(facility.commitment_amount) * rng.uniform(0.45, 1.0)
            expected_loss = ead * pd_value * lgd_value
            rows.append(
                {
                    "risk_assessment_id": f"RA{idx:09d}",
                    "application_id": facility.application_id,
                    "facility_source_id": facility.facility_source_id,
                    "rating_raw": _choice(rng, rating_variants[base_rating]),
                    "pd_raw": pd_value if rng.random() > 0.25 else f"{pd_value:.2%}",
                    "lgd_raw": lgd_value if rng.random() > 0.25 else f"{lgd_value:.0%}",
                    "ead_amount": round(ead, 2),
                    "rwa_amount": round(ead * rng.uniform(0.45, 1.25), 2),
                    "expected_loss_amount": round(expected_loss, 2),
                    "risk_model_version": _choice(rng, ["RM-2024.2", "RM-2025.1"]),
                    "assessment_date": pd.to_datetime(facility.source_extract_ts) - pd.to_timedelta(rng.integers(0, 45 + snap * 20), unit="D"),
                    "approval_level_raw": _choice(rng, ["Auto", "Local Credit", "Group Credit"]),
                    "watchlist_flag": bool(base_rating in {"B", "BB"} and rng.random() < 0.18),
                    "source_extract_ts": _source_ts(rng, 1)[0],
                }
            )
            idx += 1
    return pd.DataFrame(rows)


def _make_ftp_rates(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    months = pd.date_range("2023-01-01", "2025-12-01", freq="QS")
    product_groups = ["Committed Lines", "Term Lending", "Trade", "Guarantee"]
    for date in months:
        for currency in ["EUR", "USD", "GBP"]:
            currency_add = {"EUR": 0, "USD": 25, "GBP": 18}[currency]
            for product in product_groups:
                product_add = {"Committed Lines": 20, "Term Lending": 8, "Trade": 5, "Guarantee": 3}[product]
                for tenor in [12, 24, 36, 60, 84]:
                    rows.append(
                        {
                            "ftp_curve_date": date,
                            "currency": currency,
                            "product_group_raw": product,
                            "tenor_bucket_months": tenor,
                            "ftp_bps": round(60 + tenor * 0.8 + currency_add + product_add + rng.normal(0, 4), 2),
                            "liquidity_cost_bps": round(8 + tenor * 0.25 + (10 if product == "Committed Lines" else 0) + rng.normal(0, 2), 2),
                            "source_curve_name": "Synthetic Treasury FTP",
                            "source_extract_ts": date + pd.Timedelta(days=2),
                        }
                    )
    return pd.DataFrame(rows)


def _make_activities(opps: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    idx = 1
    activity_counts = []
    for _, opp in opps.iterrows():
        lam = 4 if bool(opp["_is_active"]) else 3
        count = int(min(14, rng.poisson(lam)))
        activity_counts.append({"opportunity_id": opp["opportunity_id"], "activity_count": count})
        for activity_no in range(count):
            rows.append(
                {
                    "activity_id": f"ACT{idx:09d}",
                    "crm_account_id": opp["crm_account_id"],
                    "opportunity_id": opp["opportunity_id"],
                    "rm_owner_code": opp["owner_rm_code"],
                    "activity_date": pd.to_datetime(opp["created_date"]) + pd.to_timedelta(rng.integers(1, 140), unit="D"),
                    "activity_type_raw": _choice(rng, ["Meeting", "Call", "Email", "Credit workshop"], p=[0.32, 0.28, 0.34, 0.06]),
                    "activity_subject_synthetic": _choice(
                        rng,
                        ["Synthetic client discussion", "Synthetic pricing follow-up", "Synthetic documentation update"],
                    ),
                    "activity_outcome_raw": _choice(rng, ["Positive", "Neutral", "Follow-up required", None], p=[0.36, 0.42, 0.17, 0.05]),
                    "next_step_raw": _choice(rng, ["Send termsheet", "Schedule credit review", "Follow up", None], p=[0.30, 0.24, 0.36, 0.10]),
                    "source_extract_ts": _source_ts(rng, 1)[0],
                }
            )
            idx += 1
    return pd.DataFrame(rows), pd.DataFrame(activity_counts)


def _standard_product_group(product_type: str) -> str:
    if product_type in {"RCF", "Overdraft"}:
        return "Committed Lines"
    if product_type == "Term Loan":
        return "Term Lending"
    if product_type == "Guarantee":
        return "Guarantee"
    return "Trade"


def _simulate_outcomes(
    opps: pd.DataFrame,
    apps: pd.DataFrame,
    facilities: pd.DataFrame,
    quotes: pd.DataFrame,
    risk: pd.DataFrame,
    relationship_strength: pd.DataFrame,
    activity_counts: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    app_to_opp = apps[["application_id", "opportunity_id"]]
    latest_quotes = (
        quotes.sort_values(["facility_source_id", "quote_version"])
        .groupby("facility_source_id", as_index=False)
        .tail(1)
    )
    facility_quote = facilities.drop_duplicates("facility_source_id").merge(
        latest_quotes[["facility_source_id", "offered_margin_bps", "floor_margin_bps"]],
        on="facility_source_id",
        how="left",
    )
    facility_quote["margin_above_floor_bps"] = (
        facility_quote["offered_margin_bps"] - facility_quote["floor_margin_bps"]
    )
    facility_quote = facility_quote.merge(app_to_opp, on="application_id", how="left")
    facility_agg = facility_quote.groupby("opportunity_id").agg(
        number_of_facilities=("facility_source_id", "nunique"),
        weighted_avg_margin_above_floor_bps=("margin_above_floor_bps", "mean"),
        anchor_product=("product_type_raw", lambda values: values.mode().iloc[0] if not values.mode().empty else "Term Loan"),
    )

    latest_risk = risk.sort_values(["facility_source_id", "assessment_date"]).groupby("facility_source_id").tail(1)
    latest_risk = latest_risk.merge(app_to_opp, on="application_id", how="left")
    rating_by_opp = latest_risk.groupby("opportunity_id")["rating_raw"].agg(lambda values: str(values.iloc[0]).upper())

    opps = opps.merge(relationship_strength, on="crm_account_id", how="left")
    opps = opps.merge(activity_counts, on="opportunity_id", how="left")
    opps = opps.merge(facility_agg, on="opportunity_id", how="left")
    opps = opps.merge(rating_by_opp.rename("rating_raw"), on="opportunity_id", how="left")
    opps["relationship_strength_score"] = opps["relationship_strength_score"].fillna(0.45)
    opps["activity_count"] = opps["activity_count"].fillna(0)
    opps["number_of_facilities"] = opps["number_of_facilities"].fillna(0)
    opps["weighted_avg_margin_above_floor_bps"] = opps["weighted_avg_margin_above_floor_bps"].fillna(55)
    opps["anchor_product"] = opps["anchor_product"].fillna("Term Loan")
    rating_penalty = opps["rating_raw"].fillna("BBB").str.lower().map(
        {"a": 0.15, "a2": 0.12, "bbb": 0.0, "baa2": 0.0, "bb": -0.22, "ba2": -0.22, "b": -0.45, "b2": -0.45}
    ).fillna(0)
    product_effect = opps["anchor_product"].map(
        {"RCF": 0.10, "Term Loan": 0.03, "Guarantee": -0.02, "Trade Finance": 0.05, "Overdraft": -0.06}
    ).fillna(0)
    latent = (
        0.25
        - 0.014 * opps["weighted_avg_margin_above_floor_bps"]
        + 1.15 * opps["relationship_strength_score"]
        + rating_penalty
        + 0.055 * np.log1p(opps["activity_count"])
        - 0.12 * opps["number_of_facilities"]
        + product_effect
        + rng.normal(0, 0.45, len(opps))
    )
    opps["_true_win_probability"] = _sigmoid(latent)

    historical_mask = ~opps["_is_active"]
    won = rng.random(len(opps)) < opps["_true_win_probability"]
    withdrawn = historical_mask & (rng.random(len(opps)) < 0.08)
    opps.loc[historical_mask & won & ~withdrawn, "stage_raw"] = "Closed Won"
    opps.loc[historical_mask & ~won & ~withdrawn, "stage_raw"] = "Closed Lost"
    opps.loc[withdrawn, "stage_raw"] = "Withdrawn"
    opps.loc[historical_mask, "actual_close_date"] = pd.to_datetime(opps.loc[historical_mask, "expected_close_date"]) + pd.to_timedelta(
        rng.integers(-20, 45, historical_mask.sum()), unit="D"
    )

    high_margin = opps["weighted_avg_margin_above_floor_bps"] > opps["weighted_avg_margin_above_floor_bps"].quantile(0.70)
    high_complexity = opps["number_of_facilities"] >= 3
    weak_relationship = opps["relationship_strength_score"] < 0.35
    weak_rating = opps["rating_raw"].fillna("").str.lower().isin(["bb", "ba2", "b", "b2"])
    lost_reasons = []
    for idx, row in opps.iterrows():
        if row["stage_raw"] != "Closed Lost":
            lost_reasons.append(None)
        elif high_margin.loc[idx] and rng.random() < 0.55:
            lost_reasons.append(_choice(rng, ["Too expensive", "Pricing"]))
        elif high_complexity.loc[idx] and rng.random() < 0.45:
            lost_reasons.append("Structure not accepted")
        elif weak_relationship.loc[idx] and rng.random() < 0.35:
            lost_reasons.append("Client chose alternative funding")
        elif weak_rating.loc[idx] and rng.random() < 0.35:
            lost_reasons.append("Credit declined")
        else:
            lost_reasons.append(_choice(rng, ["Project cancelled", "No longer needed", "Pricing", None]))
    opps["lost_reason_raw"] = lost_reasons
    opps.loc[opps["stage_raw"] == "Withdrawn", "lost_reason_raw"] = _choice(
        rng, ["No longer needed", "Project cancelled"], size=(opps["stage_raw"] == "Withdrawn").sum()
    )

    apps = apps.merge(opps[["opportunity_id", "stage_raw", "actual_close_date"]], on="opportunity_id", how="left")
    apps["application_status_raw"] = np.select(
        [
            apps["stage_raw"].eq("Closed Won"),
            apps["stage_raw"].eq("Closed Lost"),
            apps["stage_raw"].eq("Withdrawn"),
            apps["stage_raw"].isin(["Credit Review", "Negotiation"]),
        ],
        ["Approved", "Declined", "Withdrawn", "In Review"],
        default="Submitted",
    )
    apps.loc[apps["application_status_raw"].eq("Approved"), "approval_date"] = apps["actual_close_date"]
    apps.loc[apps["application_status_raw"].eq("Declined"), "decline_date"] = apps["actual_close_date"]
    apps = apps.drop(columns=["stage_raw", "actual_close_date"])

    cleanup = [
        "_is_active",
        "relationship_strength_score",
        "activity_count",
        "number_of_facilities",
        "weighted_avg_margin_above_floor_bps",
        "anchor_product",
        "rating_raw",
        "_true_win_probability",
    ]
    return opps.drop(columns=[col for col in cleanup if col in opps.columns]), apps


def generate_bronze_tables(
    n_customers: int = 500,
    n_opportunities: int = 1500,
    active_share: float = 0.25,
    random_state: int = 42,
) -> dict[str, pd.DataFrame]:
    """Generate all Bronze tables as synthetic source extracts."""

    config = BronzeGenerationConfig(n_customers, n_opportunities, active_share, random_state)
    rng = _rng(random_state)

    accounts = _make_accounts(config, rng)
    relationship_snapshots, relationship_strength = _make_relationship_snapshots(accounts, rng)
    opportunities = _make_opportunities(accounts, config, rng)
    applications = _make_applications(opportunities, rng)
    facilities = _make_facilities(applications, accounts, rng)
    quotes = _make_pricing_quotes(facilities, rng)
    risk = _make_risk_assessments(facilities, rng)
    ftp_rates = _make_ftp_rates(rng)
    activities, activity_counts = _make_activities(opportunities, rng)
    opportunities, applications = _simulate_outcomes(
        opportunities,
        applications,
        facilities,
        quotes,
        risk,
        relationship_strength,
        activity_counts,
        rng,
    )

    tables = {
        BRONZE_TABLES["crm_accounts"]: accounts,
        BRONZE_TABLES["crm_opportunities"]: opportunities,
        BRONZE_TABLES["los_applications"]: applications,
        BRONZE_TABLES["los_facilities"]: facilities,
        BRONZE_TABLES["pricing_quotes"]: quotes,
        BRONZE_TABLES["risk_assessments"]: risk,
        BRONZE_TABLES["treasury_ftp_rates"]: ftp_rates,
        BRONZE_TABLES["core_relationship_snapshot"]: relationship_snapshots,
        BRONZE_TABLES["rm_activities"]: activities,
    }
    assert_no_competitor_columns(tables)
    return tables
