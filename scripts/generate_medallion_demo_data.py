"""CLI for generating synthetic medallion demo data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from customer_pricing_analytics.medallion.pipeline import run_medallion_demo_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic medallion demo data.")
    parser.add_argument("--output-dir", default="data/generated")
    parser.add_argument("--n-customers", type=int, default=500)
    parser.add_argument("--n-opportunities", type=int, default=1500)
    parser.add_argument("--active-share", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--write-format", choices=["csv", "parquet"], default="csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_medallion_demo_pipeline(
        output_dir=args.output_dir,
        n_customers=args.n_customers,
        n_opportunities=args.n_opportunities,
        active_share=args.active_share,
        random_state=args.random_state,
        write_format=args.write_format,
    )

    print(f"Output directory: {args.output_dir}")
    for layer in ["bronze_tables", "silver_tables", "gold_tables"]:
        print(f"\n{layer}:")
        for table, count in result[layer].items():
            print(f"  {table}: {count}")

    gold = result["quality_summary"]["gold"]
    bronze = result["quality_summary"]["bronze"]
    warning_count = result["quality_summary"]["warning_count"]
    warning_denominator = max(1, len(result["bronze_tables"]) + len(result["silver_tables"]) + len(result["gold_tables"]))
    warning_share = warning_count / warning_denominator

    print("\nKey metrics:")
    print(f"  Historical training deals: {gold['training_deals']}")
    print(f"  Active scoring deals: {gold['active_scoring_deals']}")
    print(f"  Facilities: {gold['facility_economics_rows']}")
    print(f"  Outcome values: {gold['training_outcome_values']}")
    print(f"  Bronze duplicate CRM rows: {bronze['duplicate_crm_account_rows']}")
    print(f"  DQ warning share: {warning_share:.1%}")
    print("\nAll generated records are synthetic.")


if __name__ == "__main__":
    main()
