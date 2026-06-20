"""Project configuration defaults."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_WORKBOOK_PATH = DATA_DIR / "data.xlsx"

PRICING_ZONES = ("Red", "Guardrail", "Recommended", "Stretch")
