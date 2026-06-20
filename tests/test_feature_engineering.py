import pandas as pd

from customer_pricing_analytics.feature_engineering import (
    create_deal_level_features,
    create_expected_utilized_volume,
    create_margin_above_floor,
    create_tenor_years,
)


def test_create_facility_features():
    df = pd.DataFrame(
        {
            "offered_margin_bps": [150],
            "floor_margin_bps": [120],
            "tenor_months": [24],
            "commitment_amount": [1_000_000],
            "expected_utilization": [0.5],
        }
    )

    df = create_margin_above_floor(df)
    df = create_tenor_years(df)
    df = create_expected_utilized_volume(df)

    assert df.loc[0, "margin_above_floor_bps"] == 30
    assert df.loc[0, "tenor_years"] == 2
    assert df.loc[0, "expected_utilized_volume"] == 500_000


def test_create_deal_level_features():
    facility_df = pd.DataFrame(
        {
            "deal_id": ["D1", "D1", "D2"],
            "product_type": ["RCF", "Term Loan", "Guarantee"],
            "commitment_amount": [100, 200, 300],
            "expected_utilization": [0.5, 1.0, 0.2],
            "offered_margin_bps": [150, 160, 170],
            "floor_margin_bps": [100, 120, 130],
            "upfront_fee_bps": [10, 20, 30],
        }
    )

    result = create_deal_level_features(facility_df)
    d1 = result[result["deal_id"] == "D1"].iloc[0]

    assert d1["number_of_facilities"] == 2
    assert d1["total_commitment"] == 300
    assert d1["total_expected_utilized_volume"] == 250
    assert d1["min_margin_above_floor_bps"] == 40
    assert d1["has_rcf"] == True
    assert d1["has_term_loan"] == True
    assert d1["has_guarantee"] == False
