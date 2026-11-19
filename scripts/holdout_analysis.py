#!/usr/bin/env python3
"""Generalisation analysis: development set vs. held-out test set.

The agent's repair loop and the 15-item completeness rubric were written
and tuned while the first three scenarios (s01-s03) were being inspected
by hand.  The remaining scenarios were never looked at during that work,
so they form a genuine held-out set.  A rubric that only worked on the
scenarios it was tuned on would be overfitted -- exactly the bias/variance
question of the machine-learning lecture.

This script splits the results of one run into the two parts and compares
them:

    python scripts/holdout_analysis.py
    python scripts/holdout_analysis.py --run deepseek__deepseek-v4.1-flash

It writes ``results/<run>/holdout_analysis.csv`` and prints the table.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import RESULTS_DIR, latest_run_dir, list_runs   # noqa: E402

#: The scenarios that were used while the pipeline was being developed.
DEVELOPMENT_SCENARIOS = ["s01", "s02", "s03"]

METRICS = [
    ("pet_safety_compliance", "Safety"),
    ("pet_safety_compliance_resolved", "Safety*"),
    ("horticultural_viability", "Viability"),
    ("dual_constraint_accuracy", "Dual"),
    ("design_completeness", "Completeness"),
    ("design_completeness_raw", "Compl. raw /15"),
    ("design_completeness_core5", "Compl. core /5"),
]


def load(run_dir: Path) -> pd.DataFrame:
    """The per-scenario metrics of every method of one run."""
    frames = []
    for csv in sorted(run_dir.glob("metrics_*.csv")):
        try:
            df = pd.read_csv(csv)
        except (OSError, ValueError):
            continue
        if "scenario_id" not in df.columns:
            continue
        df["method"] = csv.stem.replace("metrics_", "")
        frames.append(df)
    if not frames:
        raise SystemExit(f"No metrics files in {run_dir}")
    return pd.concat(frames, ignore_index=True)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dev = df[df["scenario_id"].isin(DEVELOPMENT_SCENARIOS)]
    held = df[~df["scenario_id"].isin(DEVELOPMENT_SCENARIOS)]
    return dev, held


def summarise(df: pd.DataFrame) -> dict:
    out: dict = {"n": int(len(df))}
    for key, _ in METRICS:
        if key in df.columns:
            out[key] = float(pd.to_numeric(df[key], errors="coerce").mean())
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="development vs. held-out analysis")
    p.add_argument("--run", default=None,
                   help="run folder (default: the most recent one)")
    args = p.parse_args()

    run_dir = Path(args.run) if args.run else latest_run_dir()
    if run_dir is None:
        print("No run found. Run the experiments first:")
        for r in list_runs():
            print(f"  {r['name']}")
        return 1
    if not run_dir.is_absolute():
        for candidate in (RESULTS_DIR / "runs" / run_dir, RESULTS_DIR / run_dir):
            if candidate.is_dir():
                run_dir = candidate
                break
    if not run_dir.is_dir():
        print(f"{run_dir} does not exist.")
        return 1

    df = load(run_dir)
    dev, held = split(df)

    print("=" * 78)
    print(f"DEVELOPMENT vs. HELD-OUT   ({run_dir.name})")
    print("=" * 78)
    print(f"  development set (tuned on) : {', '.join(DEVELOPMENT_SCENARIOS)}"
          f"   n = {len(dev)} cells")
    print(f"  held-out set (never seen)  : {len(held)} cells")
    print()
    header = f"  {'method':<14}{'set':<10}" + "".join(
        f"{label:>16}" for _, label in METRICS)
    print(header)
    print("  " + "-" * (len(header) - 2))

    rows = []
    for method in sorted(df["method"].unique()):
        for name, part in (("dev", dev[dev["method"] == method]),
                           ("held-out", held[held["method"] == method])):
            if part.empty:
                continue
            s = summarise(part)
            line = f"  {method:<14}{name:<10}"
            for key, _ in METRICS:
                value = s.get(key)
                line += f"{(f'{value:.3f}' if value is not None else '-'):>16}"
            print(line)
            rows.append({"method": method, "set": name, **s})

    # the gap is the number that matters
    print()
    print("  gap (held-out - development):")
    if held.empty:
        print("  (this run only contains the development scenarios -- "
              "nothing to hold out)")
        return 0
    for method in sorted(df["method"].unique()):
        d = summarise(dev[dev["method"] == method])
        h = summarise(held[held["method"] == method])
        if not d or not h or not h.get("n"):
            continue
        parts = []
        for key, label in METRICS:
            if key in d and key in h and d[key] is not None and h[key] is not None:
                parts.append(f"{label}={h[key] - d[key]:+.3f}")
        if parts:
            print(f"    {method:<14}{'  '.join(parts)}")

    out_csv = run_dir / "holdout_analysis.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"\n  wrote {out_csv}")
    print("\n  A gap close to zero means the pipeline generalises: the "
          "rubric and the\n  repair loop are not tuned to the three "
          "scenarios they were built on.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
