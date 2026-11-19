#!/usr/bin/env python3
"""
Print the Design Completeness rubric.

The rubric is the operational definition of the completeness metric: 15
binary, machine-checkable items.  This script prints it in the two formats
the report needs, so the table in the paper can never drift from the code
that actually scores the designs.

    python scripts/print_rubric.py                # markdown
    python scripts/print_rubric.py --latex        # LaTeX table
    python scripts/print_rubric.py --check FILE   # score one saved design
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rubric import (  # noqa: E402
    DIMENSIONS,
    MAX_CORE,
    MAX_RAW,
    RUBRIC_ITEMS,
    rubric_table_latex,
    rubric_table_markdown,
    score_design,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--latex", action="store_true", help="print a LaTeX table")
    p.add_argument("--out", default=None,
                   help="write the LaTeX table to this file (e.g. report/rubric_table.tex)")
    p.add_argument("--check", default=None,
                   help="score a saved design JSON (e.g. "
                        "results/runs/<run>/agent/s01.json)")
    args = p.parse_args()

    if args.check:
        payload = json.loads(Path(args.check).read_text(encoding="utf-8"))
        design = payload.get("design", payload)
        result = score_design(design)
        print(f"Design Completeness: {result.score_raw}/{result.max_raw} "
              f"(core {result.score_core5}/{result.max_core5})")
        print("-" * 70)
        for item in RUBRIC_ITEMS:
            mark = "OK  " if result.checks[item.id] else "MISS"
            print(f"  [{mark}] {item.id}  {item.item}")
        print("-" * 70)
        for dim in DIMENSIONS:
            d = result.dimension_scores[dim]
            print(f"  {dim:<20} {d['earned']}/{d['max']}")
        return 0

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rubric_table_latex() + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
        return 0

    if args.latex:
        print(rubric_table_latex())
    else:
        print(rubric_table_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
