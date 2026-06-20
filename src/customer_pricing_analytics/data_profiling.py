"""Data profiling helpers for unknown workbook schemas."""

from pathlib import Path
from typing import Any

import pandas as pd

from customer_pricing_analytics.data_loading import load_excel_workbook


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Return a compact profile for a DataFrame."""

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "unique_values": df.nunique(dropna=True).astype(int).to_dict(),
    }


def profile_workbook(path: str | Path) -> dict[str, dict[str, Any]]:
    """Profile each sheet in an Excel workbook."""

    workbook = load_excel_workbook(path)
    return {sheet_name: profile_dataframe(df) for sheet_name, df in workbook.items()}
