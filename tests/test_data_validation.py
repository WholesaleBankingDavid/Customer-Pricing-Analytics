import pandas as pd

from customer_pricing_analytics.data_validation import validate_deal_dataset


def test_validate_deal_dataset_reports_missing_required_columns():
    df = pd.DataFrame({"deal_id": ["D1"]})

    result = validate_deal_dataset(df)

    assert result.is_valid is False
    assert "customer_id" in result.missing_columns


def test_validate_deal_dataset_warns_without_failing_on_unexpected_values():
    df = pd.DataFrame(
        {
            "deal_id": ["D1", "D1"],
            "customer_id": ["C1", "C1"],
            "deal_status": ["closed", "closed"],
            "deal_outcome": ["won", "pending"],
            "commercial_relevance_flag": [True, None],
        }
    )

    result = validate_deal_dataset(df)

    assert result.is_valid is True
    assert any("Unexpected deal_outcome" in warning for warning in result.warnings)
    assert any("duplicates" in warning for warning in result.warnings)
