# Data Generation Explained

## 1. Purpose

The synthetic data generator simulates bank-typical source systems. It does not directly create perfect model input data. The point is to show how fragmented raw data moves through Bronze, Silver, and Gold layers before it becomes suitable for modeling and RM dashboard use.

All records are synthetic. The pipeline does not create real customer names, real bank data, or competitor pricing fields.

## 2. Generated Source Systems

| Source System | Bronze Table | Business Meaning | Typical Imperfections |
| --- | --- | --- | --- |
| CRM | `bronze_crm_accounts` | Customer master and RM ownership | duplicate source rows, missing region, inconsistent segment labels |
| CRM | `bronze_crm_opportunities` | Pipeline opportunities and commercial stages | unstandardized stages, lost reasons, active deals without final outcome |
| CRM | `bronze_rm_activities` | RM calls, meetings, and emails | sparse activity history, synthetic free-text-like subjects |
| Loan Origination System | `bronze_los_applications` | Credit application or deal record | missing approval/decline dates, LOS statuses differ from CRM stages |
| Loan Origination System | `bronze_los_facilities` | Facility or product structure | mixed utilization formats, duplicate facility rows, inconsistent product naming |
| Pricing Tool | `bronze_pricing_quotes` | Quote versions per facility | multiple quote versions, missing fee fields, rare below-floor quotes |
| Risk Engine | `bronze_risk_assessments` | Rating, PD, LGD, EAD, RWA, expected loss | rating variants, numeric values as strings or percentages, older snapshots |
| Treasury | `bronze_treasury_ftp_rates` | FTP and liquidity cost curves | bucketed tenor curves, source curve snapshots |
| Core Banking / Profitability | `bronze_core_relationship_snapshot` | Existing exposure, revenue, products, contact recency | missing balances, imperfect relationship indicators |

## 3. Bronze Generation Logic

Bronze tables are generated as source-system extracts. They intentionally use source-specific identifiers and field names:

- CRM uses `crm_account_id` and `opportunity_id`.
- LOS uses `application_id` and `facility_source_id`.
- Pricing uses `quote_id` and quote versions.
- Risk uses `risk_assessment_id`.

The generated Bronze data is deliberately not perfect. IDs must be harmonized later, stage values differ between CRM and LOS, lost reasons are unstandardized, and utilization can appear as `45%`, `0.45`, or `n/a`. Pricing quotes can have multiple versions per facility. Some rows are duplicates or have missing optional values.

## 4. Customer Generation

Customers are created with synthetic legal names such as `Synthetic Manufacturing GmbH 001`. Segment, industry, region, group, RM owner, revenue bucket, and employee count are generated with realistic variation.

Large Corporate customers tend to have larger and more complex deals. Existing relationship depth, product count, revenue, and contact recency later contribute to `relationship_strength_score`.

No real names or real client identifiers are used.

## 5. Deal and Facility Generation

A customer can have multiple opportunities. An opportunity can become a LOS application. An application can contain one to four facilities.

Deal and facility are intentionally separate:

**Deal = what the RM negotiates.**

**Facility/Product = what the bank calculates.**

The outcome is simulated at Deal level. Pricing and economics are calculated at Facility/Product and PricingCase level.

## 6. Pricing Quote Generation

Each facility receives one to three quote versions to simulate negotiation. Version 1 often starts near target. Later versions can include discounts. The final quote is the latest approved or submitted quote; if none exists, the latest available quote is used and flagged.

The generator creates:

- `floor_margin_bps`
- `target_margin_bps`
- `stretch_margin_bps`
- `offered_margin_bps`
- product-dependent fees

No competitor fields are generated.

Conceptually:

```text
floor_margin_bps =
  ftp_bps
  + liquidity_cost_bps
  + risk_cost_bps
  + admin_cost_bps
  + capital_cost_bps
  + minimum_margin_buffer_bps

target_margin_bps = floor_margin_bps + target_buffer_bps
stretch_margin_bps = target_margin_bps + stretch_buffer_bps
offered_margin_bps = target_margin_bps + negotiation_noise - relationship_discount
```

The implementation approximates these relationships with synthetic product-specific floors, target buffers, stretch buffers, and random negotiation noise.

## 7. Risk and FTP Generation

Ratings influence PD. Collateral influences LGD. Product type and commitment influence EAD. RWA and expected loss are approximated but remain internally consistent.

FTP depends on currency, product group, and tenor bucket. Liquidity costs tend to be higher for longer tenors and committed lines such as RCFs.

## 8. Outcome Generation

Outcomes are simulated at Deal level, not Facility level.

```text
true_win_probability = sigmoid(
    base
    - price_sensitivity * weighted_avg_margin_above_floor_bps
    + relationship_effect * relationship_strength_score
    + rating_effect
    + rm_activity_effect
    - complexity_penalty * number_of_facilities
    + product_effect
    + noise
)
```

Higher price or higher margin above floor tends to reduce win probability. Higher margin also increases profitability, creating the desired trade-off between win probability and expected deal value.

Stronger relationships and more RM activity increase win probability. Higher deal complexity reduces win probability. Weaker ratings can reduce win probability. Active deals never receive an outcome.

Lost reasons depend on synthetic drivers:

- high price -> price
- high complexity -> structure
- weak relationship -> relationship or alternative funding
- weak rating or watchlist -> credit declined
- random share -> project cancelled or no longer needed

## 9. Bronze to Silver

Silver transformations:

- harmonize IDs
- standardize statuses
- map lost reasons
- parse expected utilization
- normalize currencies
- standardize product names
- select the final quote
- set `commercial_relevance_flag`
- keep active deals without outcomes
- exclude technical or risk-driven rejections from the modeling population where appropriate

Silver is where source-system fragments become canonical business entities.

## 10. Silver to Gold

Gold tables are analytical marts:

- `gold_facility_economics`: one row per facility with final pricing case and economics
- `gold_deal_economics`: one row per deal with facility economics aggregated
- `gold_deal_training_dataset`: closed commercial won/lost deals only
- `gold_active_deal_scoring_dataset`: active deals without outcome
- `gold_rm_deal_dashboard`: dashboard-ready active deal view

Models and dashboards should use Gold, not raw Bronze.

## 11. Leakage and Governance Rules

The generated training dataset avoids obvious leakage:

- no lost reason as a model feature
- no decision-date-derived features
- no competitor data
- no active deals in training
- no real customer data

The MVP remains pricing guidance and decision support. It is not automatic price setting.

## 12. How to Reproduce

```powershell
python scripts/generate_medallion_demo_data.py --output-dir data/generated --n-customers 500 --n-opportunities 1500 --active-share 0.25 --random-state 42
```

Generated files are written to `data/generated/bronze`, `data/generated/silver`, and `data/generated/gold`. The `data/generated/` folder is ignored by Git.
