"""Pipeline orchestration for local medallion demo data generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from customer_pricing_analytics.medallion.bronze_generator import generate_bronze_tables
from customer_pricing_analytics.medallion.bronze_to_silver import transform_bronze_to_silver
from customer_pricing_analytics.medallion.quality_checks import build_quality_summary, row_counts
from customer_pricing_analytics.medallion.silver_to_gold import transform_silver_to_gold


def _write_tables(tables: dict[str, pd.DataFrame], output_dir: Path, write_format: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, df in tables.items():
        if write_format == "csv":
            df.to_csv(output_dir / f"{table_name}.csv", index=False)
        elif write_format == "parquet":
            df.to_parquet(output_dir / f"{table_name}.parquet", index=False)
        else:
            raise ValueError("write_format must be 'csv' or 'parquet'")


def run_medallion_demo_pipeline(
    output_dir: str | Path = "data/generated",
    n_customers: int = 500,
    n_opportunities: int = 1500,
    active_share: float = 0.25,
    random_state: int = 42,
    write_format: str = "csv",
) -> dict:
    """Generate Bronze, Silver, and Gold local demo data.

    Returns row counts and a data-quality summary. All generated records are
    synthetic and written under the provided output directory.
    """

    output_path = Path(output_dir)
    bronze = generate_bronze_tables(
        n_customers=n_customers,
        n_opportunities=n_opportunities,
        active_share=active_share,
        random_state=random_state,
    )
    silver = transform_bronze_to_silver(bronze)
    gold = transform_silver_to_gold(silver)

    _write_tables(bronze, output_path / "bronze", write_format)
    _write_tables(silver, output_path / "silver", write_format)
    _write_tables(gold, output_path / "gold", write_format)

    return {
        "bronze_tables": row_counts(bronze),
        "silver_tables": row_counts(silver),
        "gold_tables": row_counts(gold),
        "quality_summary": build_quality_summary(bronze, silver, gold),
    }
