"""Write generated Mermaid diagrams to disk."""

from __future__ import annotations

from pathlib import Path

from customer_pricing_analytics.visualization.mermaid_generator import (
    generate_bronze_source_systems,
    generate_deal_facility_pricing_lineage,
    generate_field_lineage_examples,
    generate_gold_model_marts,
    generate_medallion_layer_flow,
    generate_silver_erd,
)
from customer_pricing_analytics.visualization.schema_registry import get_schema_registry


DIAGRAM_GENERATORS = {
    "medallion_layer_flow": ("medallion_layer_flow.mmd", generate_medallion_layer_flow),
    "bronze_source_systems": ("bronze_source_systems.mmd", generate_bronze_source_systems),
    "silver_entity_relationship": ("silver_entity_relationship.mmd", generate_silver_erd),
    "gold_model_marts": ("gold_model_marts.mmd", generate_gold_model_marts),
    "deal_facility_pricing_lineage": ("deal_facility_pricing_lineage.mmd", generate_deal_facility_pricing_lineage),
    "field_lineage_examples": ("field_lineage_examples.mmd", lambda registry: generate_field_lineage_examples()),
}


def write_all_diagrams(output_dir: str | Path = "docs/diagrams") -> dict[str, str]:
    """Write all Mermaid diagrams and return their paths."""

    registry = get_schema_registry()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for diagram_name, (filename, generator) in DIAGRAM_GENERATORS.items():
        target = output_path / filename
        target.write_text(generator(registry), encoding="utf-8")
        written[diagram_name] = str(target)
    return written
