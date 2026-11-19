#!/usr/bin/env python3
"""
Validate the ground-truth database and print a coverage report.

    python scripts/check_database.py

Checks
  1. the file exists, parses, and has the expected columns
  2. no empty cells, no duplicate ids, no duplicate species
  3. every controlled-vocabulary value is legal
  4. every row has a source_url
  5. coverage of the (light x moisture) matrix and of the pet-safety classes
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DATABASE_CSV, LIGHT_COMPATIBILITY, MOISTURE_COMPATIBILITY  # noqa: E402

REQUIRED = ["id", "scientific_name", "common_name", "plant_type", "light",
            "moisture", "toxic_to_cats", "toxic_to_dogs", "source_url", "notes"]
VALID_LIGHT = set(LIGHT_COMPATIBILITY)
VALID_MOISTURE = set(MOISTURE_COMPATIBILITY)
VALID_PETS = {"cat", "dog"}


def main() -> int:
    path = Path(DATABASE_CSV)
    if not path.exists():
        print(f"ERROR: {path} does not exist.")
        return 1
    df = pd.read_csv(path).fillna("")
    problems: list[str] = []

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        print(f"ERROR: missing columns {missing}")
        return 1

    # 1. empty cells
    for col in REQUIRED:
        if col in ("notes",):
            continue
        n_empty = int((df[col].astype(str).str.strip() == "").sum())
        if n_empty:
            problems.append(f"{n_empty} row(s) with an empty '{col}'")

    # 2. duplicates
    dup_id = df["id"].duplicated().sum()
    dup_sp = df["scientific_name"].str.lower().duplicated().sum()
    if dup_id:
        problems.append(f"{dup_id} duplicate id(s)")
    if dup_sp:
        problems.append(f"{dup_sp} duplicate scientific name(s)")

    # 3. vocabulary
    bad_light = sorted(set(df["light"]) - VALID_LIGHT)
    bad_moist = sorted(set(df["moisture"]) - VALID_MOISTURE)
    if bad_light:
        problems.append(f"illegal light values: {bad_light}")
    if bad_moist:
        problems.append(f"illegal moisture values: {bad_moist}")

    # 4. toxicity flags must be 0/1
    for col in ("toxic_to_cats", "toxic_to_dogs"):
        bad = sorted(set(df[col].astype(str)) - {"0", "1"})
        if bad:
            problems.append(f"illegal values in {col}: {bad}")

    # 5. sources
    n_no_source = int((df["source_url"].astype(str).str.strip() == "").sum())
    if n_no_source:
        problems.append(f"{n_no_source} row(s) without a source_url")

    # --------------------------------------------------------- report ------
    print("=" * 72)
    print(f"Ground-truth database: {path}")
    print("=" * 72)
    print(f"total species           : {len(df)}")
    safe_both = int((~df["toxic_to_cats"].astype(bool) & ~df["toxic_to_dogs"].astype(bool)).sum())
    print(f"non-toxic to both       : {safe_both}")
    print(f"toxic to cats           : {int(df['toxic_to_cats'].astype(int).sum())}")
    print(f"toxic to dogs           : {int(df['toxic_to_dogs'].astype(int).sum())}")
    print(f"distinct source pages   : {df['source_url'].nunique()}")
    print()
    print("light x moisture coverage (species per cell):")
    pivot = df.pivot_table(index="light", columns="moisture", values="id",
                           aggfunc="count", fill_value=0)
    print(pivot.to_string())
    empty_cells = [(l, m) for l in pivot.index for m in pivot.columns if pivot.loc[l, m] == 0]
    if empty_cells:
        print()
        print("WARNING empty (light, moisture) cells -> the agent will have to "
              "relax a horticultural constraint there:")
        for l, m in empty_cells:
            print(f"   {l} / {m}")
    print()
    print("plant roles:")
    print(df["plant_type"].value_counts().to_string())

    if problems:
        print()
        print("PROBLEMS FOUND:")
        for p in problems:
            print("  -", p)
        return 1
    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
