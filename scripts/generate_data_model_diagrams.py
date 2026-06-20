"""CLI for generating Mermaid data model diagrams."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from customer_pricing_analytics.visualization.diagram_writer import write_all_diagrams


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Mermaid data model diagrams.")
    parser.add_argument("--output-dir", default="docs/diagrams")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = write_all_diagrams(args.output_dir)
    print("Generated Mermaid diagrams from the Python schema registry:")
    for name, path in written.items():
        print(f"  {name}: {path}")
    print("\nMermaid .mmd files can be rendered directly in GitHub Markdown.")


if __name__ == "__main__":
    main()
