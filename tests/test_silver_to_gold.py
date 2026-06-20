from customer_pricing_analytics.medallion.bronze_generator import generate_bronze_tables
from customer_pricing_analytics.medallion.bronze_to_silver import transform_bronze_to_silver
from customer_pricing_analytics.medallion.schemas import GOLD_TABLES
from customer_pricing_analytics.medallion.silver_to_gold import transform_silver_to_gold


def _gold():
    bronze = generate_bronze_tables(n_customers=70, n_opportunities=180, random_state=9)
    silver = transform_bronze_to_silver(bronze)
    return transform_silver_to_gold(silver)


def test_gold_training_dataset_contains_only_closed_outcomes():
    gold = _gold()
    training = gold[GOLD_TABLES["deal_training_dataset"]]

    assert not training.empty
    assert set(training["deal_outcome"].unique()).issubset({"won", "lost"})


def test_gold_active_dataset_has_no_outcome():
    gold = _gold()
    active = gold[GOLD_TABLES["active_deal_scoring_dataset"]]

    assert "deal_outcome" not in active.columns
    assert "expected_close_date" in active.columns
    assert "current_stage" in active.columns


def test_gold_deal_economics_is_one_row_per_deal():
    gold = _gold()
    deal_economics = gold[GOLD_TABLES["deal_economics"]]

    assert deal_economics["deal_id"].is_unique


def test_facility_economics_contains_annual_and_lifetime_profit():
    gold = _gold()
    facility = gold[GOLD_TABLES["facility_economics"]]

    assert "expected_facility_profit_annual" in facility.columns
    assert "expected_facility_profit_lifetime" in facility.columns
    assert "pricing_zone" in facility.columns


def test_training_dataset_has_no_leakage_columns():
    gold = _gold()
    training = gold[GOLD_TABLES["deal_training_dataset"]]
    leakage_columns = {"lost_reason", "decision_date", "expected_close_date", "current_stage"}

    assert leakage_columns.isdisjoint(training.columns)
