# Input Data Generation

The medallion demo generator creates synthetic bank-like source data for the RM Deal Prioritization & Pricing Guidance MVP.

## Synthetic Sources

- `bronze_crm_accounts`: synthetic customer master records.
- `bronze_crm_opportunities`: CRM pipeline opportunities.
- `bronze_los_applications`: loan origination applications.
- `bronze_los_facilities`: structured facilities per application.
- `bronze_pricing_quotes`: quote versions per facility.
- `bronze_risk_assessments`: rating, PD, LGD, EAD, RWA, and expected loss snapshots.
- `bronze_treasury_ftp_rates`: FTP and liquidity cost curves.
- `bronze_core_relationship_snapshot`: relationship profitability snapshots.
- `bronze_rm_activities`: synthetic RM interactions.

All names, IDs, activities, and financial amounts are synthetic. No real customer data is generated or copied.

## Parameters

The pipeline can be controlled with:

- `output_dir`
- `n_customers`
- `n_opportunities`
- `active_share`
- `random_state`
- `write_format`

`random_state` makes row counts and generated IDs reproducible.

## Realistic Data Quality Issues

Bronze data deliberately includes:

- 1-3% duplicate rows in selected source extracts
- missing optional values such as region or expected utilization
- inconsistent segment labels such as `Large Corp`, `Large Corporate`, and `LC`
- inconsistent ratings such as `BBB`, `Baa2`, and `bbb`
- currencies such as `EUR`, `eur`, and `€`
- utilization values as numbers, strings, percentages, and `n/a`
- multiple quote versions per facility
- late-arriving updates through `source_extract_ts`

Silver transformations harmonize these issues without expecting perfect input.

## Outcome Simulation

Historical outcomes are simulated at deal level using a latent win-probability logic:

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

Higher margin above floor tends to reduce win probability but increase economics. Stronger relationships and more RM activity improve win probability. Higher facility complexity and weaker ratings reduce it. Active deals do not receive outcomes.

Lost reasons are generated from synthetic drivers such as price, structure, relationship, credit decline, project cancellation, or no longer needed.

## No Competitor Data

The generator does not create competitor price, competitor margin, competitor bank, or similar fields. Pricing guidance is based on internal economics, internal guardrails, risk, relationship context, and historical commercial outcomes.

For a detailed walkthrough of the generation logic and layer transformations, see `docs/data_generation_explained.md`.
