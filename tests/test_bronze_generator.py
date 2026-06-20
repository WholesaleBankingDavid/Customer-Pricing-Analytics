from customer_pricing_analytics.medallion.bronze_generator import generate_bronze_tables
from customer_pricing_analytics.medallion.schemas import BRONZE_TABLES, FORBIDDEN_COMPETITOR_TERMS


def test_bronze_generator_creates_expected_tables():
    tables = generate_bronze_tables(n_customers=50, n_opportunities=120, random_state=123)

    assert set(BRONZE_TABLES.values()).issubset(tables)
    assert len(tables[BRONZE_TABLES["crm_accounts"]]) >= 50
    assert len(tables[BRONZE_TABLES["crm_opportunities"]]) == 120
    assert len(tables[BRONZE_TABLES["los_facilities"]]) > len(tables[BRONZE_TABLES["los_applications"]])
    assert len(tables[BRONZE_TABLES["pricing_quotes"]]) > len(tables[BRONZE_TABLES["los_facilities"]])


def test_bronze_contains_intentional_dq_issues():
    tables = generate_bronze_tables(n_customers=50, n_opportunities=120, random_state=123)
    accounts = tables[BRONZE_TABLES["crm_accounts"]]
    facilities = tables[BRONZE_TABLES["los_facilities"]]

    assert accounts["crm_account_id"].duplicated().sum() > 0
    assert facilities["facility_source_id"].duplicated().sum() > 0
    assert accounts["region_raw"].isna().sum() > 0
    assert facilities["expected_utilisation_raw"].astype(str).str.lower().isin(["n/a", "nan", "none"]).sum() > 0


def test_bronze_has_no_competitor_columns():
    tables = generate_bronze_tables(n_customers=30, n_opportunities=80, random_state=12)

    for table_name, df in tables.items():
        for column in df.columns:
            assert not any(term in column.lower() for term in FORBIDDEN_COMPETITOR_TERMS), table_name
