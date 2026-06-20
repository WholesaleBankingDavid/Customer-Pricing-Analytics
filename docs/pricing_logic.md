# Pricing Logic

## Facility Economics

Risk-adjusted margin is calculated from offered margin, annualized fees, and internal cost components:

```text
risk_adjusted_margin_bps =
  offered_margin_bps
  + annualized_fee_bps
  - ftp_bps
  - liquidity_cost_bps
  - risk_cost_bps
  - admin_cost_bps
  - capital_cost_bps
```

## Facility Expected Profit

```text
expected_facility_profit =
  risk_adjusted_margin_bps / 10000
  * expected_utilized_volume
  * tenor_years
```

## Deal Economics

```text
total_expected_profit = sum(expected_facility_profit)
```

## Expected Deal Value

```text
expected_deal_value = win_probability * total_expected_profit
```

## Pricing Zones

- **Red**: below floor or negative economics.
- **Guardrail**: near floor, only with justification.
- **Recommended**: economically attractive and commercially realistic.
- **Stretch**: high margin with potentially lower win probability.

Pricing zones are guidance signals. Final pricing remains subject to RM judgment, pricing governance, risk approval, and client context.
