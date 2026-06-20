# Customer & Pricing Analytics for Wholesale Banking

This repository contains an analytics MVP for Relationship Manager (RM) deal prioritization and pricing guidance in Wholesale Banking.

The goal is to help RMs, pricing teams, and sales steering teams understand which active commercial-loan deals deserve attention, how likely a deal is to close, and whether facility-level pricing is inside an economically sensible guidance range.

The project is explicitly decision support. It does not use competitor data, does not copy real customer information into examples, and does not claim to calculate an automatically optimal price.

## MVP Use Case

**RM Deal Prioritization & Pricing Guidance**

The first realistic MVP focuses on:

- profiling available historical won/lost deal data
- separating deal-level commercial decisions from facility-level economics
- estimating baseline win probability for commercial outcomes
- calculating facility and deal economics from internal pricing guardrails
- ranking active deals by expected deal value and priority
- assigning pricing zones: `Red`, `Guardrail`, `Recommended`, `Stretch`

## Business Logic

The target data model separates four concepts:

- **Deal**: the commercial decision and negotiation object.
- **Facility/Product**: the calculation object for economics and pricing guardrails.
- **PricingCase**: the margin and fee calculation for one facility or scenario.
- **DealAnalytics**: aggregated deal assessment with win probability, expected deal value, pricing zone, and priority score.

Facility economics are aggregated to the deal level. A win/loss model estimates the probability of commercial success. Expected deal value combines both views:

```text
expected_deal_value = win_probability * total_expected_profit
```

## Methodology

The MVP starts with transparent analytics:

1. Data profiling of the available Excel workbook.
2. Descriptive win/loss analysis by product, rating, tenor, and margin buckets.
3. A baseline logistic-regression model for explainable win probability.
4. Facility-level pricing economics using internal cost and guardrail inputs.
5. Deal-level prioritization based on expected economics and model output.

The model result is not an optimal price. It is a guidance signal for human review and negotiation.

## Repository Structure

```text
README.md
docs/
  use_case_vision.md
  methodology.md
  data_model.md
  pricing_logic.md
  modeling_approach.md
  dashboard_concept.md
  open_questions.md
data/
  data.xlsx
  README.md
  data_dictionary_template.md
src/
  customer_pricing_analytics/
    config.py
    data_loading.py
    data_profiling.py
    data_validation.py
    feature_engineering.py
    pricing_economics.py
    model_training.py
    model_evaluation.py
    scoring.py
notebooks/
  01_data_profiling.ipynb
  02_baseline_win_loss_analysis.ipynb
  03_modeling_win_probability.ipynb
tests/
  test_pricing_economics.py
  test_feature_engineering.py
  test_data_validation.py
```

Existing raw notebooks are intentionally not deleted. They can be reviewed and migrated into the structured workflow over time.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

In this local workspace, a ready-to-use environment was also created as:

```powershell
.venv-win\Scripts\activate
```

## Running the MVP

Profile the workbook:

```powershell
python -c "from customer_pricing_analytics.data_profiling import profile_workbook; print(profile_workbook('data/data.xlsx'))"
```

Run tests:

```powershell
pytest
```

Open the starter notebooks:

```powershell
jupyter notebook notebooks
```

## Generating Realistic Medallion Demo Data

The repository includes a local synthetic data generator for a Bronze -> Silver -> Gold medallion flow. It simulates bank-style source systems and derives analytical marts for modeling and dashboards.

```powershell
python scripts/generate_medallion_demo_data.py --output-dir data/generated --n-customers 500 --n-opportunities 1500 --active-share 0.25 --random-state 42
```

Generated files are written to:

```text
data/generated/
  bronze/
  silver/
  gold/
```

`data/generated/` is ignored by Git. All generated records are synthetic. The generator deliberately creates realistic Bronze-layer data quality issues and then harmonizes them into Silver and Gold outputs.

## Data And Privacy

- `data/data.xlsx` is kept as the existing source workbook and is not deleted.
- New examples and tests use synthetic data only.
- Do not commit real customer names, real counterparty identifiers, or confidential pricing decisions in examples, tests, or documentation.
- The MVP must not use competitor pricing fields as model features or as pricing recommendations.

## Scope Boundaries

This repository does **not**:

- use competitive intelligence as an input to pricing decisions
- automate final price setting
- replace credit, risk, conduct, or human approval processes
- claim that the mathematically optimal price has been calculated

It provides structured pricing guidance and deal prioritization for expert review.
