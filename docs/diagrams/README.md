# Data Model Diagrams

This folder contains Mermaid diagrams generated from the Python schema registry in `src/customer_pricing_analytics/visualization/schema_registry.py`.

GitHub can render Mermaid diagrams in Markdown. The `.mmd` files can also be copied into Mermaid-compatible documentation tooling.

Regenerate all diagrams:

```powershell
python scripts/generate_data_model_diagrams.py --output-dir docs/diagrams
```

## Diagrams

- `medallion_layer_flow.mmd`: end-to-end flow from Bronze to Silver to Gold to Models and Applications.
- `bronze_source_systems.mmd`: simulated source systems and their Bronze tables.
- `silver_entity_relationship.mmd`: canonical Silver business entities and relationships.
- `gold_model_marts.mmd`: Gold datamarts and model/dashboard layer.
- `deal_facility_pricing_lineage.mmd`: business separation of Deal, Facility/Product, PricingCase, RiskAssessment, and economics.
- `field_lineage_examples.mmd`: lineage examples for margin, outcome, expected deal value, and pricing zone.
