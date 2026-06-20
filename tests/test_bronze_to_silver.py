from customer_pricing_analytics.medallion.bronze_generator import generate_bronze_tables
from customer_pricing_analytics.medallion.bronze_to_silver import transform_bronze_to_silver
from customer_pricing_analytics.medallion.schemas import SILVER_TABLES


def _silver():
    bronze = generate_bronze_tables(n_customers=60, n_opportunities=150, random_state=5)
    return transform_bronze_to_silver(bronze)


def test_silver_customer_ids_are_unique():
    silver = _silver()
    customers = silver[SILVER_TABLES["customers"]]

    assert customers["customer_id"].is_unique


def test_silver_references_are_valid():
    silver = _silver()
    customers = silver[SILVER_TABLES["customers"]]
    deals = silver[SILVER_TABLES["deals"]]
    facilities = silver[SILVER_TABLES["facilities"]]

    assert deals["customer_id"].isin(customers["customer_id"]).all()
    assert facilities["deal_id"].isin(deals["deal_id"]).all()


def test_active_deals_have_no_outcome_and_closed_commercial_deals_are_won_lost():
    silver = _silver()
    deals = silver[SILVER_TABLES["deals"]]

    active = deals[deals["deal_status"] == "active"]
    assert active["deal_outcome"].isna().all()

    closed_commercial = deals[
        deals["deal_status"].isin(["closed_won", "closed_lost"])
        & deals["commercial_relevance_flag"].eq(True)
    ]
    assert closed_commercial["deal_outcome"].isin(["won", "lost"]).all()
