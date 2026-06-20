import pytest

from customer_pricing_analytics.pricing_economics import (
    assign_pricing_zone,
    calculate_expected_deal_value,
    calculate_expected_facility_profit,
    calculate_risk_adjusted_margin_bps,
    calculate_total_expected_profit,
)


def test_calculate_risk_adjusted_margin_bps():
    assert calculate_risk_adjusted_margin_bps(
        offered_margin_bps=200,
        annualized_fee_bps=20,
        ftp_bps=50,
        liquidity_cost_bps=10,
        risk_cost_bps=25,
        admin_cost_bps=5,
        capital_cost_bps=30,
    ) == 100


def test_expected_profit_and_deal_value():
    facility_profit = calculate_expected_facility_profit(100, 1_000_000, 2)
    assert facility_profit == 20_000
    assert calculate_total_expected_profit([facility_profit, 5_000]) == 25_000
    assert calculate_expected_deal_value(0.4, 25_000) == 10_000


def test_expected_deal_value_rejects_invalid_probability():
    with pytest.raises(ValueError):
        calculate_expected_deal_value(1.5, 1000)


@pytest.mark.parametrize(
    ("offered", "risk_adjusted", "expected"),
    [
        (90, 20, "Red"),
        (105, 20, "Guardrail"),
        (150, 20, "Recommended"),
        (230, 20, "Stretch"),
        (150, -1, "Red"),
    ],
)
def test_assign_pricing_zone(offered, risk_adjusted, expected):
    assert assign_pricing_zone(
        offered_margin_bps=offered,
        floor_margin_bps=100,
        target_margin_bps=140,
        stretch_margin_bps=220,
        risk_adjusted_margin_bps=risk_adjusted,
    ) == expected
