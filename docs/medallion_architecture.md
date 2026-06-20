# Medallion Architecture

The medallion demo pipeline simulates a bank-style analytical data flow for the Customer & Pricing Analytics MVP.

## Why Not Generate Gold Directly?

Directly generating model-ready Gold tables would hide the real work of banking analytics: joining fragmented source systems, resolving identifiers, selecting final pricing versions, harmonizing statuses, and managing data quality issues. The MVP therefore creates source-like Bronze data first and derives Silver and Gold tables through explicit transformations.

## Layers

## Bronze: Raw Source-System Extracts

Bronze tables are intentionally close to source systems:

- CRM accounts and opportunities
- Loan Origination System applications and facilities
- Pricing quote versions
- Risk assessments
- Treasury FTP curves
- Core relationship snapshots
- RM activities

Bronze is slightly dirty by design: duplicate records, missing optional fields, inconsistent categories, mixed date formats, inconsistent currencies, and late-arriving updates.

## Silver: Canonical Business Entities

Silver harmonizes Bronze into canonical entities:

- Customers
- Deals
- Facilities
- Pricing cases
- Risk assessments
- Relationship snapshots
- FTP rates

Deal and Facility are deliberately separated:

- **Deal** = commercial decision and negotiation object.
- **Facility/Product** = economics and pricing calculation object.

## Gold: Analytical Data Marts

Gold tables are model- and dashboard-ready:

- Facility economics
- Deal economics
- Historical deal training dataset
- Active deal scoring dataset
- RM deal dashboard dataset

Gold data combines pricing, facility economics, risk, relationship strength, and commercial deal outcomes without using competitor data.

## Data Flow

```text
CRM / LOS / Pricing / Risk / Treasury / Core
  -> Bronze source extracts
  -> Silver canonical entities
  -> Gold analytical marts
```

Outcome is modeled at deal level. Pricing is calculated at facility and quote level. Deal economics aggregate facility economics for RM decision support.
