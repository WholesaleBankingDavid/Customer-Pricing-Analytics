"""Central schema registry used to generate Mermaid data-model diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableSchema:
    """Small metadata object for one table or application component."""

    name: str
    layer: str
    grain: str
    description: str
    primary_key: str | None
    foreign_keys: dict[str, str] = field(default_factory=dict)
    important_columns: tuple[str, ...] = field(default_factory=tuple)
    downstream_tables: tuple[str, ...] = field(default_factory=tuple)
    source_system: str | None = None


def get_schema_registry() -> dict[str, TableSchema]:
    """Return the schema registry for Bronze, Silver, Gold, and application layers."""

    registry = {
        "bronze_crm_accounts": TableSchema(
            name="bronze_crm_accounts",
            layer="bronze",
            source_system="CRM",
            grain="one row per CRM account source record",
            description="Raw synthetic CRM account extract with segment, ownership, relationship status, and source timestamps.",
            primary_key="crm_account_id",
            important_columns=(
                "crm_account_id",
                "legal_entity_name_synthetic",
                "customer_segment_raw",
                "industry_raw",
                "region_raw",
                "group_ref",
                "rm_owner_code",
                "source_extract_ts",
            ),
            downstream_tables=("silver_customers", "silver_relationship_snapshots"),
        ),
        "bronze_crm_opportunities": TableSchema(
            name="bronze_crm_opportunities",
            layer="bronze",
            source_system="CRM",
            grain="one row per CRM opportunity",
            description="Raw pipeline opportunities with CRM stages, close dates, synthetic amounts, and unstandardized lost reasons.",
            primary_key="opportunity_id",
            foreign_keys={"crm_account_id": "bronze_crm_accounts.crm_account_id"},
            important_columns=(
                "opportunity_id",
                "crm_account_id",
                "stage_raw",
                "expected_close_date",
                "actual_close_date",
                "lost_reason_raw",
                "pipeline_amount_raw",
            ),
            downstream_tables=("silver_deals",),
        ),
        "bronze_los_applications": TableSchema(
            name="bronze_los_applications",
            layer="bronze",
            source_system="Loan Origination System",
            grain="one row per loan application",
            description="Loan origination application records with LOS status, purpose, tenor, amount, and approval/decline dates.",
            primary_key="application_id",
            foreign_keys={
                "opportunity_id": "bronze_crm_opportunities.opportunity_id",
                "applicant_account_ref": "bronze_crm_accounts.crm_account_id",
            },
            important_columns=(
                "application_id",
                "opportunity_id",
                "application_status_raw",
                "financing_purpose_raw",
                "requested_amount",
                "requested_tenor_months",
            ),
            downstream_tables=("silver_deals", "silver_facilities"),
        ),
        "bronze_los_facilities": TableSchema(
            name="bronze_los_facilities",
            layer="bronze",
            source_system="Loan Origination System",
            grain="one row per facility within an application",
            description="Facility structuring extract with product, commitment, utilization, tenor, collateral, and covenant package.",
            primary_key="facility_source_id",
            foreign_keys={"application_id": "bronze_los_applications.application_id"},
            important_columns=(
                "facility_source_id",
                "application_id",
                "product_type_raw",
                "commitment_amount",
                "expected_utilisation_raw",
                "currency",
                "tenor_months",
            ),
            downstream_tables=("silver_facilities",),
        ),
        "bronze_pricing_quotes": TableSchema(
            name="bronze_pricing_quotes",
            layer="bronze",
            source_system="Pricing Tool",
            grain="one row per quote version per facility",
            description="Raw pricing quote versions with offered margin, fees, internal guardrails, approvals, and override flags.",
            primary_key="quote_id",
            foreign_keys={
                "application_id": "bronze_los_applications.application_id",
                "facility_source_id": "bronze_los_facilities.facility_source_id",
            },
            important_columns=(
                "quote_id",
                "facility_source_id",
                "quote_version",
                "quote_status_raw",
                "offered_margin_bps",
                "floor_margin_bps",
                "target_margin_bps",
                "stretch_margin_bps",
            ),
            downstream_tables=("silver_pricing_cases",),
        ),
        "bronze_risk_assessments": TableSchema(
            name="bronze_risk_assessments",
            layer="bronze",
            source_system="Risk Engine",
            grain="one row per risk assessment snapshot",
            description="Synthetic risk assessment snapshots with rating, PD, LGD, EAD, RWA, expected loss, and watchlist flags.",
            primary_key="risk_assessment_id",
            foreign_keys={
                "application_id": "bronze_los_applications.application_id",
                "facility_source_id": "bronze_los_facilities.facility_source_id",
            },
            important_columns=("risk_assessment_id", "rating_raw", "pd_raw", "lgd_raw", "ead_amount", "rwa_amount"),
            downstream_tables=("silver_risk_assessments",),
        ),
        "bronze_treasury_ftp_rates": TableSchema(
            name="bronze_treasury_ftp_rates",
            layer="bronze",
            source_system="Treasury",
            grain="one row per FTP curve date, currency, product group, and tenor bucket",
            description="Synthetic treasury FTP and liquidity cost curve extract.",
            primary_key=None,
            important_columns=("ftp_curve_date", "currency", "product_group_raw", "tenor_bucket_months", "ftp_bps", "liquidity_cost_bps"),
            downstream_tables=("silver_ftp_rates", "gold_facility_economics"),
        ),
        "bronze_core_relationship_snapshot": TableSchema(
            name="bronze_core_relationship_snapshot",
            layer="bronze",
            source_system="Core Banking",
            grain="one row per customer and month",
            description="Synthetic relationship profitability and contact snapshot for customer context.",
            primary_key=None,
            foreign_keys={"crm_account_id": "bronze_crm_accounts.crm_account_id"},
            important_columns=(
                "crm_account_id",
                "snapshot_month",
                "total_existing_exposure",
                "existing_product_count",
                "relationship_revenue_ltm",
                "days_since_last_contact",
            ),
            downstream_tables=("silver_relationship_snapshots",),
        ),
        "bronze_rm_activities": TableSchema(
            name="bronze_rm_activities",
            layer="bronze",
            source_system="CRM",
            grain="one row per RM activity",
            description="Synthetic RM meeting, call, and email activities linked to account and opportunity.",
            primary_key="activity_id",
            foreign_keys={
                "crm_account_id": "bronze_crm_accounts.crm_account_id",
                "opportunity_id": "bronze_crm_opportunities.opportunity_id",
            },
            important_columns=("activity_id", "crm_account_id", "opportunity_id", "activity_type_raw", "activity_outcome_raw"),
            downstream_tables=("silver_deals", "gold_deal_training_dataset"),
        ),
        "silver_customers": TableSchema(
            name="silver_customers",
            layer="silver",
            grain="one row per harmonized customer",
            description="Canonical customer entity deduplicated from CRM account records.",
            primary_key="customer_id",
            important_columns=("customer_id", "crm_account_id", "customer_segment", "industry", "region", "rm_id", "is_active_customer"),
            downstream_tables=("silver_deals", "silver_relationship_snapshots", "gold_deal_training_dataset"),
        ),
        "silver_deals": TableSchema(
            name="silver_deals",
            layer="silver",
            grain="one row per harmonized commercial deal",
            description="Canonical Deal entity representing the commercial negotiation and outcome object.",
            primary_key="deal_id",
            foreign_keys={"customer_id": "silver_customers.customer_id"},
            important_columns=(
                "deal_id",
                "customer_id",
                "opportunity_id",
                "application_id",
                "deal_status",
                "deal_outcome",
                "lost_reason",
                "commercial_relevance_flag",
                "rm_id",
            ),
            downstream_tables=("silver_facilities", "gold_deal_economics", "gold_deal_training_dataset"),
        ),
        "silver_facilities": TableSchema(
            name="silver_facilities",
            layer="silver",
            grain="one row per harmonized facility or product",
            description="Canonical Facility/Product entity used as the pricing and economics calculation object.",
            primary_key="facility_id",
            foreign_keys={"deal_id": "silver_deals.deal_id"},
            important_columns=(
                "facility_id",
                "deal_id",
                "product_type",
                "commitment_amount",
                "expected_utilization",
                "expected_utilized_volume",
                "tenor_months",
            ),
            downstream_tables=("silver_pricing_cases", "silver_risk_assessments", "gold_facility_economics"),
        ),
        "silver_pricing_cases": TableSchema(
            name="silver_pricing_cases",
            layer="silver",
            grain="one row per harmonized quote version",
            description="Canonical PricingCase entity with final quote flag, margins, fees, and guardrails.",
            primary_key="pricing_case_id",
            foreign_keys={"deal_id": "silver_deals.deal_id", "facility_id": "silver_facilities.facility_id"},
            important_columns=(
                "pricing_case_id",
                "facility_id",
                "quote_id",
                "quote_version",
                "is_final_quote",
                "offered_margin_bps",
                "floor_margin_bps",
                "target_margin_bps",
                "stretch_margin_bps",
            ),
            downstream_tables=("gold_facility_economics",),
        ),
        "silver_risk_assessments": TableSchema(
            name="silver_risk_assessments",
            layer="silver",
            grain="one row per selected risk assessment per facility",
            description="Canonical risk inputs used for facility economics and deal-level modeling features.",
            primary_key="risk_assessment_id",
            foreign_keys={"deal_id": "silver_deals.deal_id", "facility_id": "silver_facilities.facility_id"},
            important_columns=("risk_assessment_id", "facility_id", "rating", "pd", "lgd", "ead", "rwa", "expected_loss"),
            downstream_tables=("gold_facility_economics", "gold_deal_training_dataset"),
        ),
        "silver_relationship_snapshots": TableSchema(
            name="silver_relationship_snapshots",
            layer="silver",
            grain="one row per customer and month",
            description="Harmonized relationship context including relationship strength score.",
            primary_key=None,
            foreign_keys={"customer_id": "silver_customers.customer_id"},
            important_columns=("customer_id", "snapshot_month", "relationship_strength_score", "existing_product_count", "days_since_last_contact"),
            downstream_tables=("gold_deal_training_dataset", "gold_active_deal_scoring_dataset"),
        ),
        "gold_facility_economics": TableSchema(
            name="gold_facility_economics",
            layer="gold",
            grain="one row per facility with final pricing case",
            description="Facility-level economics and pricing zone based on final pricing case, risk, FTP, and internal costs.",
            primary_key="facility_id",
            foreign_keys={"deal_id": "silver_deals.deal_id", "facility_id": "silver_facilities.facility_id"},
            important_columns=(
                "deal_id",
                "facility_id",
                "risk_adjusted_margin_bps",
                "expected_facility_profit_annual",
                "expected_facility_profit_lifetime",
                "pricing_zone",
            ),
            downstream_tables=("gold_deal_economics",),
        ),
        "gold_deal_economics": TableSchema(
            name="gold_deal_economics",
            layer="gold",
            grain="one row per deal",
            description="Deal-level aggregated economics and product mix from facility-level economics.",
            primary_key="deal_id",
            foreign_keys={"deal_id": "silver_deals.deal_id", "customer_id": "silver_customers.customer_id"},
            important_columns=(
                "deal_id",
                "customer_id",
                "anchor_product",
                "number_of_facilities",
                "total_expected_profit_lifetime",
                "deal_pricing_zone",
            ),
            downstream_tables=("gold_deal_training_dataset", "gold_active_deal_scoring_dataset", "gold_rm_deal_dashboard"),
        ),
        "gold_deal_training_dataset": TableSchema(
            name="gold_deal_training_dataset",
            layer="gold",
            grain="one row per historical commercial won/lost deal",
            description="Leakage-controlled training dataset for win-probability modeling.",
            primary_key="deal_id",
            foreign_keys={"deal_id": "gold_deal_economics.deal_id"},
            important_columns=("deal_id", "customer_segment", "rating_at_offer", "relationship_strength_score", "deal_outcome"),
            downstream_tables=("win_probability_model",),
        ),
        "gold_active_deal_scoring_dataset": TableSchema(
            name="gold_active_deal_scoring_dataset",
            layer="gold",
            grain="one row per active deal",
            description="Model-ready active deal dataset without outcome labels.",
            primary_key="deal_id",
            foreign_keys={"deal_id": "gold_deal_economics.deal_id"},
            important_columns=("deal_id", "expected_close_date", "current_stage", "pricing_zone", "total_expected_profit_lifetime"),
            downstream_tables=("pricing_guidance", "rm_deal_cockpit"),
        ),
        "gold_rm_deal_dashboard": TableSchema(
            name="gold_rm_deal_dashboard",
            layer="gold",
            grain="one row per active deal for RM dashboard",
            description="Dashboard-ready active deal mart for RM prioritization and pricing guidance.",
            primary_key="deal_id",
            foreign_keys={"deal_id": "gold_active_deal_scoring_dataset.deal_id"},
            important_columns=("deal_id", "rm_id", "pricing_zone", "total_commitment", "recommended_action_placeholder"),
            downstream_tables=("rm_deal_cockpit",),
        ),
        "win_probability_model": TableSchema(
            name="win_probability_model",
            layer="model",
            grain="trained model artifact",
            description="Predictive model trained on historical commercial won/lost deals.",
            primary_key=None,
            important_columns=("features", "win_probability", "calibration_metrics"),
            downstream_tables=("pricing_guidance", "rm_deal_cockpit"),
        ),
        "pricing_guidance": TableSchema(
            name="pricing_guidance",
            layer="application",
            grain="one guidance record per active deal",
            description="Decision-support guidance combining economics, pricing zones, and win probability.",
            primary_key="deal_id",
            foreign_keys={"deal_id": "gold_active_deal_scoring_dataset.deal_id"},
            important_columns=("deal_id", "win_probability", "expected_deal_value", "pricing_zone"),
            downstream_tables=("rm_deal_cockpit",),
        ),
        "rm_deal_cockpit": TableSchema(
            name="rm_deal_cockpit",
            layer="application",
            grain="RM-facing dashboard view",
            description="Front-end concept for RM deal prioritization and pricing guidance.",
            primary_key=None,
            important_columns=("deal_priority", "win_probability", "expected_deal_value", "facility_guardrails"),
            downstream_tables=(),
        ),
    }
    return registry


def get_tables_by_layer(layer: str) -> dict[str, TableSchema]:
    """Return registry entries for a specific layer."""

    return {
        name: schema
        for name, schema in get_schema_registry().items()
        if schema.layer == layer
    }
