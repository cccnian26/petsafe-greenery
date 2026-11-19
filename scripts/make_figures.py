#!/usr/bin/env python3
"""
Turn the experiment metrics into the figures used in the report and slides.

    python scripts/make_figures.py

Figures produced (all saved as PNG + PDF in figures/):
    fig1_main_metrics.png    -- the four headline metrics for the three methods
    fig2_safety_by_scenario.png -- per-scenario safety compliance
    fig3_breakdown.png       -- safety / viability by pet configuration
    fig4_db_composition.png  -- the composition of the ground-truth database
    fig5_tool_effect.png     -- how grounding and filtering each add value
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import (FIGURES_DIR, RESULTS_DIR, latest_run_dir)  # noqa: E402
from src.db import get_database                                # noqa: E402

METHOD_LABEL = {
    "agent": "Proposed\ndual-constraint agent",
    "zeroshot": "Baseline 1\nzero-shot LLM",
    "naive_rag": "Baseline 2\nnaive keyword RAG",
}
ORDER = ["zeroshot", "naive_rag", "agent"]
COLORS = {"zeroshot": "#c44e52", "naive_rag": "#dd8452", "agent": "#4c72b0"}


def load(results_dir: Path) -> pd.DataFrame:
    frames = []
    for method in ORDER:
        path = results_dir / f"metrics_{method}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["method"] = method
            frames.append(df)
    if not frames:
        raise SystemExit(
            f"No metrics files found in {results_dir}. Run scripts/run_experiments.py first."
        )
    return pd.concat(frames, ignore_index=True)


def fig1_main_metrics(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    metrics = [
        ("pet_safety_compliance", "Pet safety\ncompliance"),
        ("horticultural_viability", "Horticultural\nviability"),
        ("dual_constraint_accuracy", "Dual-constraint\naccuracy"),
        ("design_completeness", "Design\ncompleteness"),
    ]
    methods = [m for m in ORDER if m in set(df["method"])]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2))
    for ax, (col, title) in zip(axes, metrics):
        vals = [df[df.method == m][col].mean() * 100 for m in methods]
        bars = ax.bar([METHOD_LABEL[m] for m in methods], vals,
                      color=[COLORS[m] for m in methods], width=0.62)
        ax.set_title(title, fontsize=12, weight="bold")
        ax.set_ylim(0, 105)
        ax.set_ylabel("%")
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.1f}",
                    ha="center", fontsize=10, weight="bold")
        ax.tick_params(axis="x", labelsize=8)
    if watermark:
        fig.suptitle(watermark, fontsize=13, color="crimson", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93 if watermark else 1])
    fig.savefig(out / "fig1_main_metrics.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig1_main_metrics.pdf", bbox_inches="tight")
    plt.close(fig)


def fig2_safety_by_scenario(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    methods = [m for m in ORDER if m in set(df["method"])]
    scenarios = sorted(set(df["scenario_id"]))
    fig, ax = plt.subplots(figsize=(14, 4.8))
    width = 0.8 / max(len(methods), 1)
    x = range(len(scenarios))
    for i, m in enumerate(methods):
        sub = df[df.method == m].set_index("scenario_id")
        vals = [sub.loc[s, "pet_safety_compliance"] * 100 if s in sub.index else 0
                for s in scenarios]
        ax.bar([p + i * width for p in x], vals, width=width,
               label=METHOD_LABEL[m].replace("\n", " "), color=COLORS[m])
    ax.set_xticks([p + 0.4 for p in x])
    ax.set_xticklabels(scenarios, rotation=90, fontsize=8)
    ax.set_ylabel("Pet safety compliance (%)")
    ax.set_title("Per-scenario pet safety compliance", fontsize=13, weight="bold")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.legend(fontsize=9, ncol=3)
    if watermark:
        fig.suptitle(watermark, fontsize=13, color="crimson", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92 if watermark else 1])
    fig.savefig(out / "fig2_safety_by_scenario.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig2_safety_by_scenario.pdf", bbox_inches="tight")
    plt.close(fig)


def fig3_breakdown(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    df = df.copy()
    df["pet_group"] = df["pets"].apply(
        lambda p: ("no pet" if not str(p).strip()
                   else " + ".join(str(p).split("|")) if "|" in str(p)
                   else str(p).strip())
    )
    groups = ["cat", "dog", "cat + dog", "no pet"]
    methods = [m for m in ORDER if m in set(df["method"])]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, col, title in (
        (axes[0], "pet_safety_compliance", "Pet safety compliance"),
        (axes[1], "dual_constraint_accuracy", "Dual-constraint accuracy"),
    ):
        for m in methods:
            sub = df[df.method == m]
            vals = [sub[sub.pet_group == g][col].mean() * 100 if g in set(sub.pet_group) else 0
                    for g in groups]
            ax.plot(groups, vals, marker="o", linewidth=2, label=METHOD_LABEL[m].replace("\n", " "),
                    color=COLORS[m])
        ax.set_title(title, fontsize=12, weight="bold")
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.3, linestyle="--")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    if watermark:
        fig.suptitle(watermark, fontsize=13, color="crimson", weight="bold")
    fig.savefig(out / "fig3_breakdown.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig3_breakdown.pdf", bbox_inches="tight")
    plt.close(fig)


def fig4_db_composition(out: Path) -> None:
    db = get_database()
    stats = db.stats()
    df = db.df
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

    counts = [
        ("non-toxic to both", stats["safe_for_both"]),
        ("toxic to cats", stats["toxic_to_cats"]),
        ("toxic to dogs", stats["toxic_to_dogs"]),
    ]
    names = [c[0] for c in counts]
    vals = [c[1] for c in counts]
    axes[0].bar(names, vals, color=["#55a868", "#c44e52", "#dd8452"])
    axes[0].set_title(f"Ground-truth database (N={stats['total']})", weight="bold")
    axes[0].set_ylabel("species")
    for i, v in enumerate(vals):
        axes[0].text(i, v + 0.6, str(v), ha="center", weight="bold")
    axes[0].tick_params(axis="x", labelsize=8)

    light_counts = df["light"].value_counts()
    axes[1].bar(light_counts.index, light_counts.values, color="#4c72b0")
    axes[1].set_title("Species by light requirement", weight="bold")
    axes[1].set_ylabel("species")
    axes[1].tick_params(axis="x", labelsize=8, rotation=15)

    type_counts = df["plant_type"].value_counts()
    axes[2].barh(type_counts.index, type_counts.values, color="#8172b3")
    axes[2].set_title("Species by planting role", weight="bold")
    axes[2].set_xlabel("species")
    axes[2].tick_params(axis="y", labelsize=8)

    fig.tight_layout()
    fig.savefig(out / "fig4_db_composition.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig4_db_composition.pdf", bbox_inches="tight")
    plt.close(fig)


def fig5_tool_effect(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    """Cumulative effect: no grounding -> grounding -> grounding + filtering.

    Every number is read from the measured metrics; nothing is hard-coded.
    """
    labels = ["Zero-shot LLM\n(no grounding)",
              "+ keyword retrieval\n(no safety filter)",
              "+ deterministic safety\nfilter & audit"]
    keys = ["zeroshot", "naive_rag", "agent"]
    safety, dual = [], []
    for k in keys:
        sub = df[df.method == k]
        safety.append(round(sub["pet_safety_compliance"].mean() * 100, 1) if len(sub) else 0.0)
        dual.append(round(sub["dual_constraint_accuracy"].mean() * 100, 1) if len(sub) else 0.0)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = range(len(labels))
    ax.plot(x, safety, marker="o", linewidth=2.5, label="Pet safety compliance")
    ax.plot(x, dual, marker="s", linewidth=2.5, label="Dual-constraint accuracy")
    for xi, v in zip(x, safety):
        ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, weight="bold")
    for xi, v in zip(x, dual):
        ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=9, weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("%")
    ax.set_ylim(0, 110)
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    ax.set_title("Where the improvement comes from", weight="bold")
    if watermark:
        fig.suptitle(watermark, fontsize=12, color="crimson", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93 if watermark else 1])
    fig.savefig(out / "fig5_tool_effect.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig5_tool_effect.pdf", bbox_inches="tight")
    plt.close(fig)


def fig6_rubric_items(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    """Pass rate per rubric item -- shows exactly which design knowledge each
    method is missing."""
    from src.rubric import RUBRIC_ITEMS

    methods = [m for m in ORDER if m in set(df["method"])]
    items = [i for i in RUBRIC_ITEMS]
    labels = [f"{i.id}  {i.item}" for i in items]

    fig, ax = plt.subplots(figsize=(11, 8.2))
    height = 0.8 / max(len(methods), 1)
    y = range(len(items))
    for k, m in enumerate(methods):
        sub = df[df.method == m]
        vals = []
        for i in items:
            col = f"check_{i.id}"
            vals.append(float(sub[col].mean()) * 100 if col in sub.columns and len(sub) else 0.0)
        ax.barh([p + k * height for p in y], vals, height=height,
                label=METHOD_LABEL[m].replace("\n", " "), color=COLORS[m])
    ax.set_yticks([p + 0.4 for p in y])
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("pass rate (%)")
    ax.set_title("Design Completeness rubric: pass rate per item", fontsize=13, weight="bold")
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.legend(fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.06))
    if watermark:
        fig.suptitle(watermark, fontsize=12, color="crimson", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94 if watermark else 1])
    fig.savefig(out / "fig6_rubric_items.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig6_rubric_items.pdf", bbox_inches="tight")
    plt.close(fig)


def fig7_completeness_dimensions(df: pd.DataFrame, out: Path, watermark: str = "") -> None:
    """Dimension-level completeness: zoning / combination / care / cautions."""
    from src.rubric import DIMENSIONS

    methods = [m for m in ORDER if m in set(df["method"])]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    width = 0.8 / max(len(methods), 1)
    x = range(len(DIMENSIONS))
    for k, m in enumerate(methods):
        sub = df[df.method == m]
        vals = []
        for dim in DIMENSIONS:
            col = f"dimfrac_{dim}"
            vals.append(float(sub[col].mean()) * 100 if col in sub.columns and len(sub) else 0.0)
        ax.bar([p + k * width for p in x], vals, width=width,
               label=METHOD_LABEL[m].replace("\n", " "), color=COLORS[m])
    ax.set_xticks([p + 0.4 for p in x])
    ax.set_xticklabels(DIMENSIONS, fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_ylabel("items passed (%)")
    ax.set_title("Design Completeness by dimension", fontsize=13, weight="bold")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.legend(fontsize=9, ncol=3)
    if watermark:
        fig.suptitle(watermark, fontsize=12, color="crimson", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92 if watermark else 1])
    fig.savefig(out / "fig7_completeness_dimensions.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "fig7_completeness_dimensions.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default=None,
                   help="folder holding metrics_<method>.csv "
                        "(default: the results of the most recent run)")
    p.add_argument("--figures", default=str(FIGURES_DIR))
    p.add_argument("--allow-offline", action="store_true",
                   help="allow building figures from simulated (offline) results")
    args = p.parse_args()

    if args.results:
        results_dir = Path(args.results)
    else:
        results_dir = latest_run_dir()
    if results_dir is None:
        print("No finished run found under results/runs/.")
        print("Run the experiments first:")
        print("    python scripts\\run_experiments.py --backend deepseek")
        print("Or point at a specific run:")
        print("    python scripts\\make_figures.py --results results\\runs\\<run>")
        return 1
    out = Path(args.figures)
    out.mkdir(parents=True, exist_ok=True)

    watermark = ""
    _simulated = "offline_demo" in str(results_dir)
    _manifest = results_dir / "manifest.json"
    if _manifest.is_file():
        try:
            _simulated = bool(json.loads(
                _manifest.read_text(encoding="utf-8")).get("simulated"))
        except (OSError, ValueError):
            pass
    if _simulated:
        if not args.allow_offline:
            raise SystemExit(
                "Refusing to build report figures from SIMULATED offline results.\n"
                "Run a real experiment first (export GEMINI_API_KEY=... ), or pass "
                "--allow-offline if you only want to preview the chart layout."
            )
        watermark = "OFFLINE DEMO - SIMULATED DATA, NOT EXPERIMENTAL RESULTS"

    df = load(results_dir)
    fig1_main_metrics(df, out, watermark)
    fig2_safety_by_scenario(df, out, watermark)
    fig3_breakdown(df, out, watermark)
    fig4_db_composition(out)
    fig5_tool_effect(df, out, watermark)
    fig6_rubric_items(df, out, watermark)
    fig7_completeness_dimensions(df, out, watermark)

    # A manifest so that anybody (including scripts/fill_report.py) can tell
    # which run produced these figures.  Without it, a figure left over from
    # the offline demo would be indistinguishable from a real one.
    try:
        manifest = json.loads((results_dir / "manifest.json")
                              .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    figures = sorted(p.name for p in out.glob("fig*.pdf"))
    (out / "figures_manifest.json").write_text(json.dumps({
        "results_dir": str(results_dir),
        "run": manifest.get("run", results_dir.name),
        "backend": manifest.get("backend", ""),
        "model": manifest.get("model", ""),
        "timestamp": manifest.get("timestamp", ""),
        "simulated": bool(_simulated),
        "watermark": watermark,
        "figures": figures,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"figures written to {out}")
    print(f"  they belong to run: {manifest.get('model', '?')} "
          f"({results_dir.name})")
    if _simulated:
        print("  !! SIMULATED -- these must not go into the report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
