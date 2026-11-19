#!/usr/bin/env python3
"""
Create clearly-marked placeholder panels for the report figures.

The real figures are produced by scripts/make_figures.py AFTER a real
experiment has been run.  These placeholders exist so that the report
skeleton compiles out of the box; they are replaced automatically the first
time the student runs the real experiment.

    python scripts/make_placeholder_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.config import FIGURES_DIR  # noqa: E402

# (name, caption, (width, height) in inches) -- the sizes mirror the real
# figures in scripts/make_figures.py, so the report paginates identically
# before and after the real experiment.
PANELS = [
    ("fig1_main_metrics", "Headline metrics for the three methods", (16, 4.2)),
    ("fig2_safety_by_scenario", "Per-scenario pet safety compliance", (14, 4.8)),
    ("fig3_breakdown", "Breakdown by pet configuration", (12, 4.4)),
    ("fig4_db_composition", "Composition of the ground-truth database", (14, 4.2)),
    ("fig5_tool_effect", "Where the improvement comes from", (8, 4.4)),
    ("fig6_rubric_items", "Design Completeness rubric: pass rate per item", (11, 8.2)),
    ("fig7_completeness_dimensions", "Design Completeness by dimension", (10, 4.6)),
]


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for name, title, (w, h) in PANELS:
        fig, ax = plt.subplots(figsize=(w, h))
        ax.set_facecolor("#f4f4f6")
        ax.text(0.5, 0.58, "PLACEHOLDER", ha="center", va="center",
                fontsize=22 * min(w, h) / 7.0, weight="bold", color="#9aa0a6")
        ax.text(0.5, 0.40, title, ha="center", va="center",
                fontsize=11 * min(w, h) / 7.0, color="#5f6368")
        ax.text(0.5, 0.20,
                "replace with:  python scripts/run_experiments.py  ->  "
                "python scripts/make_figures.py",
                ha="center", va="center", fontsize=9 * min(w, h) / 7.0,
                style="italic", color="#80868b")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#dadce0")
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(FIGURES_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"wrote {len(PANELS)} placeholder panels to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
