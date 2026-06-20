"""Generate Mermaid diagrams from the schema registry."""

from __future__ import annotations

from collections.abc import Mapping
import re

from customer_pricing_analytics.visualization.schema_registry import TableSchema, get_schema_registry


def _node_id(name: str) -> str:
    node_id = re.sub(r"[^0-9A-Za-z_]", "_", name)
    node_id = re.sub(r"_+", "_", node_id).strip("_")
    if node_id and node_id[0].isdigit():
        node_id = f"n_{node_id}"
    return node_id


def _label(name: str) -> str:
    return name.replace("_", "<br/>")


def _registry(schema_registry: Mapping[str, TableSchema] | None = None) -> Mapping[str, TableSchema]:
    return schema_registry or get_schema_registry()


def generate_medallion_layer_flow(schema_registry: Mapping[str, TableSchema] | None = None) -> str:
    """Generate Bronze -> Silver -> Gold -> Models/Dashboard flowchart."""

    registry = _registry(schema_registry)
    layers = [
        ("Bronze", "bronze"),
        ("Silver", "silver"),
        ("Gold", "gold"),
        ("Models and Applications", "model"),
        ("Models and Applications", "application"),
    ]
    lines = ["flowchart LR"]
    emitted_subgraphs: set[str] = set()
    for title, layer in layers:
        if title not in emitted_subgraphs:
            lines.append(f"  subgraph {title.replace(' ', '_')}[{title}]")
            for name, schema in registry.items():
                if schema.layer == layer or (title == "Models and Applications" and schema.layer in {"model", "application"}):
                    lines.append(f"    {_node_id(name)}[{_label(name)}]")
            lines.append("  end")
            emitted_subgraphs.add(title)
    for name, schema in registry.items():
        for downstream in schema.downstream_tables:
            if downstream in registry:
                lines.append(f"  {_node_id(name)} --> {_node_id(downstream)}")
    return "\n".join(lines) + "\n"


def generate_bronze_source_systems(schema_registry: Mapping[str, TableSchema] | None = None) -> str:
    """Generate source system to Bronze table flowchart."""

    registry = _registry(schema_registry)
    lines = ["flowchart LR"]
    source_nodes: dict[str, str] = {}
    for name, schema in registry.items():
        if schema.layer != "bronze" or not schema.source_system:
            continue
        source_id = _node_id(schema.source_system)
        source_nodes[schema.source_system] = source_id
        lines.append(f"  {source_id}(({schema.source_system})) --> {_node_id(name)}[{_label(name)}]")
    return "\n".join(lines) + "\n"


def generate_silver_erd(schema_registry: Mapping[str, TableSchema] | None = None) -> str:
    """Generate Mermaid ERD for Silver canonical business entities."""

    _registry(schema_registry)
    return "\n".join(
        [
            "erDiagram",
            "  silver_customers ||--o{ silver_deals : owns",
            "  silver_deals ||--o{ silver_facilities : contains",
            "  silver_facilities ||--o{ silver_pricing_cases : priced_by",
            "  silver_facilities ||--o{ silver_risk_assessments : assessed_by",
            "  silver_customers ||--o{ silver_relationship_snapshots : has",
            "  silver_customers {",
            "    string customer_id PK",
            "    string crm_account_id",
            "    string customer_segment",
            "    string rm_id",
            "  }",
            "  silver_deals {",
            "    string deal_id PK",
            "    string customer_id FK",
            "    string deal_status",
            "    string deal_outcome",
            "  }",
            "  silver_facilities {",
            "    string facility_id PK",
            "    string deal_id FK",
            "    string product_type",
            "    float expected_utilized_volume",
            "  }",
            "  silver_pricing_cases {",
            "    string pricing_case_id PK",
            "    string facility_id FK",
            "    float offered_margin_bps",
            "    bool is_final_quote",
            "  }",
            "  silver_risk_assessments {",
            "    string risk_assessment_id PK",
            "    string facility_id FK",
            "    string rating",
            "    float pd",
            "  }",
            "  silver_relationship_snapshots {",
            "    string customer_id FK",
            "    date snapshot_month",
            "    float relationship_strength_score",
            "  }",
            "",
        ]
    )


def generate_gold_model_marts(schema_registry: Mapping[str, TableSchema] | None = None) -> str:
    """Generate Gold marts to model/application layer flowchart."""

    _registry(schema_registry)
    return "\n".join(
        [
            "flowchart LR",
            "  gold_facility_economics[gold<br/>facility<br/>economics] --> gold_deal_economics[gold<br/>deal<br/>economics]",
            "  gold_deal_economics --> gold_deal_training_dataset[gold<br/>deal<br/>training<br/>dataset]",
            "  gold_deal_economics --> gold_active_deal_scoring_dataset[gold<br/>active<br/>deal<br/>scoring<br/>dataset]",
            "  gold_deal_training_dataset --> win_probability_model((win probability model))",
            "  gold_active_deal_scoring_dataset --> pricing_guidance[pricing guidance]",
            "  win_probability_model --> pricing_guidance",
            "  pricing_guidance --> gold_rm_deal_dashboard[gold<br/>RM deal<br/>dashboard]",
            "  gold_rm_deal_dashboard --> rm_deal_cockpit((RM deal cockpit))",
            "",
        ]
    )


def generate_deal_facility_pricing_lineage(schema_registry: Mapping[str, TableSchema] | None = None) -> str:
    """Generate business lineage for Deal vs Facility/Pricing separation."""

    _registry(schema_registry)
    return "\n".join(
        [
            "flowchart TB",
            "  deal[Deal<br/>commercial decision and negotiation object]",
            "  facility[Facility/Product<br/>economics and pricing calculation object]",
            "  pricing_case[PricingCase<br/>price fee and guardrail version]",
            "  risk_assessment[RiskAssessment<br/>risk input]",
            "  facility_economics[FacilityEconomics<br/>economics per facility]",
            "  deal_economics[DealEconomics<br/>aggregated economics per deal]",
            "  deal --> facility",
            "  facility --> pricing_case",
            "  facility --> risk_assessment",
            "  pricing_case --> facility_economics",
            "  risk_assessment --> facility_economics",
            "  facility --> facility_economics",
            "  facility_economics --> deal_economics",
            "  deal --> deal_economics",
            "",
        ]
    )


def generate_field_lineage_examples() -> str:
    """Generate field lineage examples for key MVP fields."""

    return "\n".join(
        [
            "flowchart LR",
            "  bq_margin[bronze_pricing_quotes.offered_margin_bps] --> sp_margin[silver_pricing_cases.offered_margin_bps]",
            "  sp_margin --> gf_margin[gold_facility_economics.offered_margin_bps]",
            "  gf_margin --> gd_margin[gold_deal_economics.weighted_avg_margin_above_floor_bps]",
            "  gd_margin --> pricing_guidance[pricing_guidance]",
            "",
            "  crm_stage[bronze_crm_opportunities.stage_raw / lost_reason_raw] --> sd_outcome[silver_deals.deal_outcome]",
            "  los_status[bronze_los_applications.application_status_raw] --> sd_outcome",
            "  sd_outcome --> training_target[gold_deal_training_dataset.deal_outcome]",
            "  training_target --> win_probability_model[win_probability_model target]",
            "",
            "  gd_profit[gold_deal_economics.total_expected_profit_lifetime] --> expected_value[scoring expected_deal_value]",
            "  model_probability[model win_probability] --> expected_value",
            "  expected_value --> dashboard_priority[gold_rm_deal_dashboard.priority_rank]",
            "",
            "  guardrails[silver_pricing_cases.floor_margin_bps / target_margin_bps / stretch_margin_bps] --> facility_zone[gold_facility_economics.pricing_zone]",
            "  risk_margin[gold_facility_economics.risk_adjusted_margin_bps] --> facility_zone",
            "  facility_zone --> deal_zone[gold_deal_economics.deal_pricing_zone]",
            "  deal_zone --> cockpit[rm_deal_cockpit]",
            "",
        ]
    )
