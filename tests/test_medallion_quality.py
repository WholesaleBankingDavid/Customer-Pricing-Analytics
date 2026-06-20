from customer_pricing_analytics.medallion.pipeline import run_medallion_demo_pipeline
from pathlib import Path
import shutil
import uuid


def _temp_output_dir(name: str) -> Path:
    path = Path(".tmp") / "medallion-tests" / f"{name}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_pipeline_writes_medallion_layers():
    output_dir = _temp_output_dir("layers")
    result = run_medallion_demo_pipeline(
        output_dir=output_dir,
        n_customers=40,
        n_opportunities=100,
        active_share=0.25,
        random_state=42,
    )

    assert (output_dir / "bronze").exists()
    assert (output_dir / "silver").exists()
    assert (output_dir / "gold").exists()
    assert result["bronze_tables"]
    assert result["silver_tables"]
    assert result["gold_tables"]
    assert "warnings" in result["quality_summary"]
    shutil.rmtree(output_dir, ignore_errors=True)


def test_pipeline_is_reproducible_for_row_counts_and_ids():
    output_dir = _temp_output_dir("repro")
    first = run_medallion_demo_pipeline(
        output_dir=output_dir / "first",
        n_customers=40,
        n_opportunities=100,
        active_share=0.25,
        random_state=7,
    )
    second = run_medallion_demo_pipeline(
        output_dir=output_dir / "second",
        n_customers=40,
        n_opportunities=100,
        active_share=0.25,
        random_state=7,
    )

    assert first["bronze_tables"] == second["bronze_tables"]
    assert first["silver_tables"] == second["silver_tables"]
    assert first["gold_tables"] == second["gold_tables"]

    first_accounts = (output_dir / "first" / "bronze" / "bronze_crm_accounts.csv").read_text().splitlines()
    second_accounts = (output_dir / "second" / "bronze" / "bronze_crm_accounts.csv").read_text().splitlines()
    assert first_accounts[1].split(",")[0] == second_accounts[1].split(",")[0]
    shutil.rmtree(output_dir, ignore_errors=True)
