#!/usr/bin/env python3
"""Compare the results of two (or more) models side by side.

Every run lives in its own folder (``results/runs/<provider>__<model>/``),
so two models can be compared without either of them being overwritten.

    python scripts/compare_models.py                 # every finished run
    python scripts/compare_models.py --csv           # also write the CSV
    python scripts/compare_models.py --latex         # LaTeX table for the report
    python scripts/compare_models.py --runs gemini__gemini-3.5-flash-lite \
                                           deepseek__deepseek-v4.1-flash

Outputs (in ``results/``):
    model_comparison.csv     one row per (run, method)
    model_comparison.md      the same table, readable
    model_comparison.tex     a LaTeX table for the report
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import RESULTS_DIR, list_runs                       # noqa: E402

# The columns that matter for the comparison, in report order.
METRICS = [
    ("pet_safety_compliance", "Safety", 8),
    ("pet_safety_compliance_resolved", "Safety*", 8),
    ("horticultural_viability", "Viability", 9),
    ("dual_constraint_accuracy", "Dual", 8),
    ("design_completeness", "Completeness", 11),
]
METHOD_ORDER = ["agent", "zeroshot", "naive_rag"]
METHOD_LABEL = {"agent": "Agent (ours)",
                "zeroshot": "Zero-shot",
                "naive_rag": "Naive RAG"}


def load_run(run: dict) -> pd.DataFrame | None:
    """The summary table of one run, with the run's identity added."""
    path = Path(run["path"]) / "summary.csv"
    if not path.is_file():
        return None
    try:
        df = pd.read_csv(path)
    except (OSError, ValueError):
        return None
    if df.empty:
        return None
    df["run"] = run["name"]
    df["backend"] = run.get("backend", "")
    df["model"] = run.get("model", "")
    df["timestamp"] = run.get("timestamp", "")
    df["simulated"] = str(run.get("simulated", "")).lower() in ("true", "1") or (
        run.get("backend") == "offline")
    if "n_scenarios" not in df.columns:
        df["n_scenarios"] = 0
    return df


def collect(runs: list[dict], include_simulated: bool = False) -> pd.DataFrame:
    frames = []
    for run in runs:
        df = load_run(run)
        if df is None:
            continue
        if not include_simulated and bool(df["simulated"].iloc[0]):
            continue
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["method_order"] = out["method"].map(
        {m: i for i, m in enumerate(METHOD_ORDER)}).fillna(99)
    out = out.sort_values(["run", "method_order"]).drop(columns=["method_order"])
    return out.reset_index(drop=True)


def fmt(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "--"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


NOTE = ("Safety = the conservative number (ASPCA-certified species only).\n"
        "Safety* = the resolved number (secondary source admitted).")


def print_table(df: pd.DataFrame) -> None:
    if df.empty:
        print("No finished runs found under results/runs/.")
        print("Run the experiments first:")
        print("    python scripts\\run_experiments.py --backend deepseek")
        return
    for run_name, group in df.groupby("run", sort=False):
        model = group["model"].iloc[0] or "?"
        backend = group["backend"].iloc[0] or "?"
        n = int(pd.to_numeric(group["n_scenarios"], errors="coerce").fillna(0).max())
        stamp = group["timestamp"].iloc[0] or ""
        print("=" * 78)
        print(f"{run_name}")
        print(f"  provider: {backend}   model: {model}   "
              f"scenarios: {n}   {stamp}")
        print("-" * 78)
        header = f"  {'method':<14}" + "".join(
            f"{label:>{width}}" for _, label, width in METRICS)
        print(header)
        for _, row in group.iterrows():
            line = f"  {METHOD_LABEL.get(row['method'], row['method']):<14}"
            for key, _, width in METRICS:
                line += f"{fmt(row.get(key)):>{width}}"
            print(line)
        print()

    print(NOTE)
    print()
    if df["run"].nunique() > 1:
        print("=" * 78)
        print("SAME METHOD, DIFFERENT MODELS")
        print("-" * 78)
        for method in METHOD_ORDER:
            sub = df[df["method"] == method]
            if sub.empty or sub["run"].nunique() < 2:
                continue
            print(f"  {METHOD_LABEL.get(method, method)}")
            for _, row in sub.iterrows():
                cells = "  ".join(
                    f"{label}={fmt(row.get(key))}" for key, label, _ in METRICS)
                print(f"    {row['model'] or row['run']:<28} {cells}")
            print()


def write_csv(df: pd.DataFrame, out: Path) -> None:
    keep = ["run", "backend", "model", "method", "n_scenarios", "timestamp"]
    keep += [k for k, _, _ in METRICS]
    keep += ["design_completeness_raw_mean", "design_completeness_core5_mean",
             "mean_recommendations_per_design", "mean_seconds_per_design"]
    keep = [c for c in keep if c in df.columns]
    df[keep].to_csv(out, index=False)
    print(f"  wrote {out}")


def write_markdown(df: pd.DataFrame, out: Path) -> None:
    if df.empty:
        return
    lines = ["| run | model | method | safety | viability | dual | completeness |",
             "|---|---|---|---|---|---|---|"]
    for _, row in df.iterrows():
        lines.append(
            f"| {row['run']} | {row.get('model', '')} | "
            f"{METHOD_LABEL.get(row['method'], row['method'])} | "
            f"{fmt(row.get('pet_safety_compliance'))} | "
            f"{fmt(row.get('horticultural_viability'))} | "
            f"{fmt(row.get('dual_constraint_accuracy'))} | "
            f"{fmt(row.get('design_completeness'))} |")
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print(f"  wrote {out}")


def write_latex(df: pd.DataFrame, out: Path) -> None:
    if df.empty:
        return
    lines = [
        "% generated by scripts/compare_models.py -- do not edit by hand",
        "\\begin{tabular}{ll l r r r r}", "\\toprule",
        "Provider & Model & Method & Safety & Viab. & Dual & Compl.\\\\",
        "\\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{row.get('backend', '')} & {row.get('model', '')} & "
            f"{METHOD_LABEL.get(row['method'], row['method'])} & "
            f"{fmt(row.get('pet_safety_compliance'))} & "
            f"{fmt(row.get('horticultural_viability'))} & "
            f"{fmt(row.get('dual_constraint_accuracy'))} & "
            f"{fmt(row.get('design_completeness'))} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print(f"  wrote {out}")


def main() -> int:
    p = argparse.ArgumentParser(description="compare the results of two models")
    p.add_argument("--runs", nargs="+", default=None,
                   help="only these run folders (default: every finished run)")
    p.add_argument("--include-simulated", action="store_true",
                   help="also show the offline demo (simulated) results")
    p.add_argument("--csv", action="store_true", help="write model_comparison.csv")
    p.add_argument("--markdown", action="store_true",
                   help="write model_comparison.md")
    p.add_argument("--latex", action="store_true", help="write model_comparison.tex")
    p.add_argument("--all", action="store_true",
                   help="write all three output files")
    args = p.parse_args()

    runs = list_runs()
    if args.runs:
        wanted = set(args.runs)
        runs = [r for r in runs if r["name"] in wanted]
        if not runs:
            print(f"None of {sorted(wanted)} was found under {RESULTS_DIR / 'runs'}")
            print("Available runs:")
            for r in list_runs():
                print(f"  {r['name']}")
            return 1
    df = collect(runs, include_simulated=args.include_simulated)
    print_table(df)

    out_dir = RESULTS_DIR
    wrote = False
    if args.all or args.csv:
        write_csv(df, out_dir / "model_comparison.csv")
        wrote = True
    if args.all or args.markdown:
        write_markdown(df, out_dir / "model_comparison.md")
        wrote = True
    if args.all or args.latex:
        write_latex(df, out_dir / "model_comparison.tex")
        wrote = True
    if not wrote:
        print("Tip: add --all to write the CSV / Markdown / LaTeX table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
