"""Workbook loading helpers with defensive error handling."""

from pathlib import Path
from typing import Any

import pandas as pd


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Workbook not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Expected a file path, got: {resolved}")
    return resolved


def load_excel_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    """Load every sheet in an Excel workbook.

    The function makes no assumptions about sheet names or required columns.
    """

    workbook_path = _resolve_path(path)
    try:
        return pd.read_excel(workbook_path, sheet_name=None)
    except ValueError as exc:
        raise ValueError(f"Unable to read Excel workbook {workbook_path}: {exc}") from exc


def list_sheets(path: str | Path) -> list[str]:
    """Return sheet names for an Excel workbook."""

    workbook_path = _resolve_path(path)
    try:
        return pd.ExcelFile(workbook_path).sheet_names
    except ValueError as exc:
        raise ValueError(f"Unable to inspect Excel workbook {workbook_path}: {exc}") from exc


def load_sheet(path: str | Path, sheet_name: str, **read_excel_kwargs: Any) -> pd.DataFrame:
    """Load one sheet from a workbook."""

    workbook_path = _resolve_path(path)
    available_sheets = list_sheets(workbook_path)
    if sheet_name not in available_sheets:
        raise ValueError(
            f"Sheet '{sheet_name}' not found in {workbook_path}. "
            f"Available sheets: {available_sheets}"
        )
    return pd.read_excel(workbook_path, sheet_name=sheet_name, **read_excel_kwargs)
