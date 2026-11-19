#!/usr/bin/env python3
"""
Draw the agent workflow figure used in the report (figures/fig_workflow.pdf).

    python scripts/make_workflow_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.config import FIGURES_DIR  # noqa: E402

LLM_BG, PY_BG = "#dbe9f6", "#fde8d7"
LLM_EDGE, PY_EDGE = "#3f6ea8", "#b06a2c"


def box(ax, x, y, w, h, title, lines, llm=True, fs_title=10, fs_body=7.8):
    fc, ec = (LLM_BG, LLM_EDGE) if llm else (PY_BG, PY_EDGE)
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.010,rounding_size=0.02",
                                linewidth=1.6, edgecolor=ec, facecolor=fc))
    ax.text(x + w / 2, y + h - 0.045, title, ha="center", va="top",
            fontsize=fs_title, weight="bold", color=ec, linespacing=1.25)
    ax.text(x + w / 2, y + h - 0.135, "\n".join(lines), ha="center", va="top",
            fontsize=fs_body, color="#222222", linespacing=1.5)


def arrow(ax, p1, p2, rad=0.0, label=None, lx=None, ly=None, color="#555555"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.4, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx = lx if lx is not None else (p1[0] + p2[0]) / 2
        my = ly if ly is not None else (p1[1] + p2[1]) / 2
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                color="#333333",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"))


def main() -> int:
    fig, ax = plt.subplots(figsize=(12.0, 5.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    TOP_Y, H = 0.60, 0.30

    box(ax, 0.010, TOP_Y, 0.135, H, "User brief",
        ["'a north-facing", "balcony, one cat'"], llm=False)
    box(ax, 0.180, TOP_Y, 0.160, H, "1  Constraint\nextraction",
        ["LLM parses light,", "moisture and the", "household pets"], llm=True)
    box(ax, 0.375, TOP_Y, 0.170, H, "2  Deterministic\nfilter",
        ["Python over the ground-", "truth database: drop", "every toxic species,", "keep the viable ones"], llm=False)
    box(ax, 0.580, TOP_Y, 0.165, H, "3  Design\nsynthesis",
        ["LLM composes zones,", "combination logic,", "care and cautions"], llm=True)
    box(ax, 0.780, TOP_Y, 0.135, H, "Final design",
        ["zones, care,", "cautions, safety", "note"], llm=False)

    for x1, x2 in ((0.145, 0.180), (0.340, 0.375), (0.545, 0.580), (0.745, 0.780)):
        arrow(ax, (x1, TOP_Y + H / 2), (x2, TOP_Y + H / 2))
    ax.text(0.460, TOP_Y + H + 0.045, "tool call: query_pet_safe_plants",
            ha="center", fontsize=7.8, color="#333333")

    box(ax, 0.285, 0.16, 0.185, 0.25, "4a  Safety audit",
        ["Python re-checks every", "species for toxicity", "and viability"], llm=False)
    box(ax, 0.545, 0.16, 0.215, 0.25, "4b  Completeness rubric",
        ["Python checks 15 items:", "zoning, combination,", "care, cautions"],
        llm=False, fs_title=9.5)

    arrow(ax, (0.662, TOP_Y), (0.400, 0.41), rad=0.18, label="audit", lx=0.505, ly=0.475)
    arrow(ax, (0.470, 0.285), (0.545, 0.285), label="violations", lx=0.5075, ly=0.335)
    arrow(ax, (0.640, 0.41), (0.668, TOP_Y), rad=-0.16, label="repair", lx=0.695, ly=0.475)

    ax.text(0.5, 0.055,
            "The pet-safety filter is never relaxed; horticultural constraints may be "
            "relaxed along a documented ladder (moisture first, then light).",
            ha="center", va="center", fontsize=8.2, style="italic", color="#444444")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "fig_workflow.pdf", bbox_inches="tight")
    fig.savefig(FIGURES_DIR / "fig_workflow.png", dpi=200, bbox_inches="tight")
    print(f"wrote {FIGURES_DIR / 'fig_workflow.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
