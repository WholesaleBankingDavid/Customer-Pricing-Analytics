# Data Dictionary Template

Use this template when documenting source fields.

| Field name | Entity | Data type | Required | Description | Example allowed | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| deal_id | Deal | string | yes | Unique deal identifier | synthetic only | Do not use real client identifiers in examples |
| facility_id | Facility | string | yes | Unique facility identifier | synthetic only | One deal can have multiple facilities |
| offered_margin_bps | PricingCase | numeric | yes | Offered margin in basis points | 175 | Internal pricing input |
| floor_margin_bps | PricingCase | numeric | yes | Minimum guardrail margin | 120 | Internal guardrail |
| deal_outcome | Deal | string | no | Historical commercial outcome | won/lost | Exclude non-commercial outcomes from modeling |

Extend this template for each source table or workbook sheet before production use.
