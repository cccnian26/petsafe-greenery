#!/usr/bin/env python3
"""Turn the experiment results into the JSON the slides read.

    python scripts/make_slide_data.py                  # newest run
    python scripts/make_slide_data.py --run deepseek__deepseek-v4.1-flash

Writes ``slides/data/results.json``.  The slide scripts fill their tables
from that file, so the deck always shows the numbers that were actually
measured -- never a number typed by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import RESULTS_DIR, latest_run_dir, list_runs   # noqa: E402

OUT = ROOT / "slides" / "data" / "results.json"

METHOD_LABEL = {"agent": "Proposed agent",
                "zeroshot": "B1 zero-shot",
                "naive_rag": "B2 naive RAG"}
METHOD_ORDER = ["zeroshot", "naive_rag", "agent"]


def num(value: object, digits: int = 3, dash: str = "-") -> str:
    if value is None:
        return dash
    try:
        f = float(value)
    except (TypeError, ValueError):
        return dash
    if pd.isna(f):
        return dash
    return f"{f:.{digits}f}"


def build(run_dir: Path) -> dict:
    summary_path = run_dir / "summary.csv"
    if not summary_path.is_file():
        raise SystemExit(f"No summary.csv in {run_dir}. Run the experiments first.")
    df = pd.read_csv(summary_path)

    manifest = {}
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    rows = []
    for method in METHOD_ORDER:
        sub = df[df["method"] == method]
        if sub.empty:
            rows.append({"method": METHOD_LABEL[method], "safety": "-",
                         "viability": "-", "dual": "-", "completeness": "-",
                         "oodb": "-", "raw": "-", "core": "-"})
            continue
        r = sub.iloc[0]
        rows.append({
            "method": METHOD_LABEL[method],
            "safety": num(r.get("pet_safety_compliance")),
            "viability": num(r.get("horticultural_viability")),
            "dual": num(r.get("dual_constraint_accuracy")),
            "completeness": num(r.get("design_completeness")),
            "oodb": num(r.get("out_of_database_rate")),
            "raw": num(r.get("design_completeness_raw_mean"), 1),
            "core": num(r.get("design_completeness_core5_mean"), 1),
            "n_scenarios": int(r.get("n_scenarios", 0) or 0),
            "plants": num(r.get("total_recommended_plants"), 0),
            "toxic": num(r.get("total_toxic_recommendations"), 0),
            "seconds": num(r.get("mean_seconds_per_design"), 1),
        })

    usage = {}
    try:
        usage = json.loads((run_dir / "usage.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    rubric = []
    rb_path = run_dir / "rubric_breakdown.csv"
    if rb_path.is_file():
        rb = pd.read_csv(rb_path)
        for _, r in rb.iterrows():
            rubric.append({
                "item": str(r.get("item", "")),
                "name": str(r.get("name", "")),
                "rate": num(r.get("agent_rate", r.get("rate", ""))),
            })

    return {
        "run": run_dir.name,
        "model": manifest.get("model", ""),
        "backend": manifest.get("backend", ""),
        "provider": manifest.get("provider", ""),
        "code_version": manifest.get("code_version", ""),
        "timestamp": manifest.get("timestamp", ""),
        "n_scenarios": manifest.get("n_scenarios", 0),
        "rows": rows,
        "usage": {
            "calls": usage.get("calls", 0),
            "cache_hits": usage.get("cache_hits", 0),
            "total_seconds": usage.get("total_seconds", 0.0),
            "model": usage.get("model", manifest.get("model", "")),
        },
        "rubric": rubric,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="build slides/data/results.json")
    p.add_argument("--run", default=None,
                   help="run folder (default: the most recent one)")
    p.add_argument("--out", default=str(OUT))
    args = p.parse_args()

    if args.run:
        run_dir = RESULTS_DIR / "runs" / args.run
        if not run_dir.is_dir():
            run_dir = RESULTS_DIR / args.run
    else:
        run_dir = latest_run_dir()
    if run_dir is None or not Path(run_dir).is_dir():
        print("No run found. Run the experiments first, or pass --run <name>.")
        print("Known runs:")
        for r in list_runs():
            print(f"  {r['name']}  ({r.get('model', '')})")
        return 1

    data = build(Path(run_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}  (run: {data['run']}, model: {data['model']})")
    for row in data["rows"]:
        print(f"  {row['method']:<16} safety={row['safety']:<6} "
              f"viab={row['viability']:<6} dual={row['dual']:<6} "
              f"compl={row['completeness']:<6} oodb={row['oodb']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
