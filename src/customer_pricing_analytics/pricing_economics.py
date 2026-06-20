"""Pricing economics calculations for facility and deal guidance."""

from collections.abc import Iterable


def calculate_risk_adjusted_margin_bps(
    offered_margin_bps: float,
    annualized_fee_bps: float = 0.0,
    ftp_bps: float = 0.0,
    liquidity_cost_bps: float = 0.0,
    risk_cost_bps: float = 0.0,
    admin_cost_bps: float = 0.0,
    capital_cost_bps: float = 0.0,
) -> float:
    """Calculate internal risk-adjusted margin in basis points."""

    return (
        offered_margin_bps
        + annualized_fee_bps
        - ftp_bps
        - liquidity_cost_bps
        - risk_cost_bps
        - admin_cost_bps
        - capital_cost_bps
    )


def calculate_expected_facility_profit(
    risk_adjusted_margin_bps: float,
    expected_utilized_volume: float,
    tenor_years: float,
) -> float:
    """Calculate expected profit for one facility."""

    return risk_adjusted_margin_bps / 10000 * expected_utilized_volume * tenor_years


def calculate_total_expected_profit(expected_facility_profits: Iterable[float]) -> float:
    """Aggregate facility expected profits to deal level."""

    return float(sum(expected_facility_profits))


def calculate_expected_deal_value(
    win_probability: float,
    total_expected_profit: float,
) -> float:
    """Calculate probability-weighted expected deal value."""

    if not 0 <= win_probability <= 1:
        raise ValueError("win_probability must be between 0 and 1")
    return win_probability * total_expected_profit


def assign_pricing_zone(
    offered_margin_bps: float,
    floor_margin_bps: float,
    target_margin_bps: float,
    stretch_margin_bps: float,
    risk_adjusted_margin_bps: float | None = None,
    guardrail_buffer_bps: float = 10.0,
) -> str:
    """Assign a pricing guidance zone.

    Red indicates below-floor or negative economics. Guardrail indicates near-floor
    pricing that needs justification. Recommended indicates target-level pricing.
    Stretch indicates high-margin pricing that may reduce win probability.
    """

    if offered_margin_bps < floor_margin_bps:
        return "Red"
    if risk_adjusted_margin_bps is not None and risk_adjusted_margin_bps < 0:
        return "Red"
    if offered_margin_bps <= floor_margin_bps + guardrail_buffer_bps:
        return "Guardrail"
    if offered_margin_bps >= stretch_margin_bps:
        return "Stretch"
    if offered_margin_bps >= target_margin_bps:
        return "Recommended"
    return "Guardrail"
