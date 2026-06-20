# Target Data Model

The target model separates commercial negotiation from product economics.

**Facility/Product = calculation object.**

**Deal = decision and negotiation object.**

**DealAnalytics aggregates facility economics and models the deal outcome.**

## Customer

- customer_id
- segment
- industry
- region
- group_id
- rm_id
- rating_current

## Deal

- deal_id
- customer_id
- deal_name
- deal_status
- deal_type
- offer_date
- decision_date
- expected_close_date
- deal_outcome
- lost_reason
- commercial_relevance_flag

## Facility

- facility_id
- deal_id
- product_type
- commitment_amount
- drawn_amount
- expected_utilization
- currency
- tenor_months
- maturity_date
- collateral_type

## PricingCase

- pricing_case_id
- deal_id
- facility_id
- offered_margin_bps
- upfront_fee_bps
- commitment_fee_bps
- utilization_fee_bps
- ftp_bps
- liquidity_cost_bps
- risk_cost_bps
- admin_cost_bps
- capital_cost_bps
- floor_margin_bps
- target_margin_bps
- stretch_margin_bps
- gross_margin_bps
- net_margin_bps
- margin_above_floor_bps

## RiskAssessment

- risk_assessment_id
- deal_id
- facility_id
- rating
- pd
- lgd
- ead
- rwa
- expected_loss

## DealAnalytics

- deal_id
- win_probability
- total_expected_profit
- expected_deal_value
- pricing_zone
- priority_score
- key_driver_1
- key_driver_2
- key_driver_3

## RMFeedback

- feedback_id
- deal_id
- rm_id
- feedback_date
- feedback_type
- rm_comment
- recommendation_accepted_flag
- actual_outcome

## Aggregation Logic

Facility-level pricing cases produce margin and expected profit metrics. Deal-level analytics aggregate these metrics by `deal_id` and combine them with a commercial win probability model. The deal remains the negotiation object; the facility remains the pricing calculation object.
