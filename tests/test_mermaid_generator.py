from customer_pricing_analytics.visualization.diagram_writer import write_all_diagrams
from customer_pricing_analytics.visualization.mermaid_generator import (
    generate_bronze_source_systems,
    generate_deal_facility_pricing_lineage,
    generate_field_lineage_examples,
    generate_gold_model_marts,
    generate_medallion_layer_flow,
    generate_silver_erd,
)
from customer_pricing_analytics.visualization.schema_registry import get_schema_registry


def test_medallion_layer_flow_contains_all_layers():
    diagram = generate_medallion_layer_flow(get_schema_registry())

    assert diagram.startswith("flowchart")
    assert "Bronze" in diagram
    assert "Silver" in diagram
    assert "Gold" in diagram
    assert "Models and Applications" in diagram


def test_bronze_source_systems_contains_expected_sources():
    diagram = generate_bronze_source_systems(get_schema_registry())

    assert "CRM" in diagram
    assert "Loan Origination System" in diagram
    assert "Pricing Tool" in diagram
    assert "Risk Engine" in diagram
    assert "Treasury" in diagram
    assert "Core Banking" in diagram
    assert "Loan Origination System((" not in diagram
    assert "Pricing Tool((" not in diagram
    assert "Risk Engine((" not in diagram
    assert "Core Banking((" not in diagram
    assert "Loan_Origination_System((Loan Origination System))" in diagram


def test_silver_erd_contains_required_relationships():
    diagram = generate_silver_erd(get_schema_registry())

    assert diagram.startswith("erDiagram")
    assert "silver_customers ||--o{ silver_deals" in diagram
    assert "silver_facilities ||--o{ silver_pricing_cases" in diagram


def test_gold_and_lineage_diagrams_contain_business_concepts():
    gold = generate_gold_model_marts(get_schema_registry())
    lineage = generate_deal_facility_pricing_lineage(get_schema_registry())
    fields = generate_field_lineage_examples()

    assert "win_probability_model" in gold
    assert "rm_deal_cockpit" in gold
    assert "Deal<br/>commercial decision" in lineage
    assert "Facility/Product<br/>economics" in lineage
    assert "bronze_pricing_quotes.offered_margin_bps" in fields
    assert "gold_deal_training_dataset.deal_outcome" in fields


def test_write_all_diagrams_writes_expected_files():
    output_dir = ".tmp/diagram-tests"
    written = write_all_diagrams(output_dir)

    assert set(written) == {
        "medallion_layer_flow",
        "bronze_source_systems",
        "silver_entity_relationship",
        "gold_model_marts",
        "deal_facility_pricing_lineage",
        "field_lineage_examples",
    }
