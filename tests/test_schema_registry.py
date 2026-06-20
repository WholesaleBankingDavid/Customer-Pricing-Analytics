from customer_pricing_analytics.visualization.schema_registry import get_schema_registry


def test_schema_registry_contains_required_layers_and_tables():
    registry = get_schema_registry()

    required = {
        "bronze_crm_accounts",
        "bronze_crm_opportunities",
        "bronze_los_applications",
        "bronze_los_facilities",
        "bronze_pricing_quotes",
        "bronze_risk_assessments",
        "bronze_treasury_ftp_rates",
        "bronze_core_relationship_snapshot",
        "bronze_rm_activities",
        "silver_customers",
        "silver_deals",
        "silver_facilities",
        "silver_pricing_cases",
        "silver_risk_assessments",
        "silver_relationship_snapshots",
        "gold_facility_economics",
        "gold_deal_economics",
        "gold_deal_training_dataset",
        "gold_active_deal_scoring_dataset",
        "gold_rm_deal_dashboard",
        "win_probability_model",
        "pricing_guidance",
        "rm_deal_cockpit",
    }

    assert required.issubset(registry)
    assert {schema.layer for schema in registry.values()} >= {"bronze", "silver", "gold", "model", "application"}


def test_silver_deals_metadata_documents_key_fields():
    silver_deals = get_schema_registry()["silver_deals"]

    assert silver_deals.primary_key == "deal_id"
    assert silver_deals.foreign_keys["customer_id"] == "silver_customers.customer_id"
    assert "deal_outcome" in silver_deals.important_columns
    assert "commercial_relevance_flag" in silver_deals.important_columns


def test_bronze_tables_have_source_systems():
    registry = get_schema_registry()
    bronze = [schema for schema in registry.values() if schema.layer == "bronze"]

    assert bronze
    assert all(schema.source_system for schema in bronze)
