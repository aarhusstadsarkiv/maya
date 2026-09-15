#!/usr/bin/env python3
"""Export the configured facet labels as an indented text file."""

import argparse
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from maya.settings_facets import settings_facets  # noqa: E402


def add_facets(lines: list[str], facets: list[dict[str, Any]], level: int) -> None:
    for facet in facets:
        lines.append(f"{'  ' * level}{facet['label']}")
        add_facets(lines, facet.get("children", []), level + 1)


def export_facets(output_path: Path) -> None:
    lines: list[str] = []

    for facet_group in settings_facets.values():
        lines.append(facet_group["label"])
        add_facets(lines, facet_group.get("content", []), 1)
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("facets.txt"),
        help="output file (default: facets.txt)",
    )
    args = parser.parse_args()
    export_facets(args.output)
    print(f"Wrote facets to {args.output}")
