#!/usr/bin/env python3
"""Rebuild the unfilled template of the report.

The report keeps every measured number as a ``\\todo{}`` marker.  This
script turns a filled report back into that template, so that a run with a
different model can be filled in from scratch.

    python scripts\\make_report_template.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEX = ROOT / "report" / "report_skeleton.tex"
TEMPLATE = ROOT / "report" / "report_skeleton.template.tex"

HEAD_TODO = "\\todo{} & \\todo{} & \\todo{} & \\todo{} & \\todo{} & \\todo{} \\\\"
COMP_TODO = "\\todo{} & \\todo{} &  & \\todo{} & \\todo{} \\\\"
# two closing braces: one for the \todo{...}, one for the {\footnotesize ...}
FOOT_TODO = ("\\todo{Insert both and state the difference\n"
             "explicitly in the text.}}")
ANALYSIS_TODO = (
    '\\todo{Discuss: (i) why the agent\'s safety rate is exactly 1.0 --- the '
    "filter\nis deterministic, so the model is never given the opportunity to "
    "choose an\nunsafe species, rather than the model being \"more careful\"; "
    "(ii) why the\nbaselines' viability is competitive while their safety is "
    "not --- the two\nconstraint families are independent, and grounding alone "
    "fixes only one of\nthem; (iii) the incremental value of retrieval (B1 vs "
    "B2) and of negative\nfiltering (B2 vs proposed); (iv) a concrete failure "
    "case, e.g. a zero-shot\ndesign in which a true lily was proposed for a "
    "cat household.}")


def main() -> int:
    if not TEX.is_file():
        print(f"{TEX} not found")
        return 1
    lines = TEX.read_text(encoding="utf-8").split("\n")

    # --- the two tables ------------------------------------------------
    table = 0
    for i, line in enumerate(lines):
        if line.startswith("Baseline 1 (zero-shot) &") or \
                line.startswith("Baseline 2 (naive RAG) &") or \
                line.startswith("\\textbf{Proposed (agent)} &"):
            label = line.split(" &")[0]
            # the headline table has six columns, the completeness table five
            todo = HEAD_TODO if line.count("&") >= 6 else COMP_TODO
            lines[i] = f"{label} & {todo}"
            table += 1
        if table >= 6:
            break

    text = "\n".join(lines)

    # --- the footnote --------------------------------------------------
    start = text.find("(Section~\\ref{sec:resolving}). The agent's two numbers")
    if start != -1:
        end = text.find("\n", start)
        head = text[:start]
        tail = text[end:]
        text = head + "(Section~\\ref{sec:resolving}). " + FOOT_TODO + tail

    # --- the analysis paragraph ----------------------------------------
    start = text.find("(i) The agent's pet-safety compliance")
    if start != -1:
        end = text.find("\n", start)
        text = text[:start] + ANALYSIS_TODO + text[end:]

    TEMPLATE.write_text(text, encoding="utf-8")
    n = text.count("\\todo{}")
    print(f"wrote {TEMPLATE}")
    print(f"  \\todo{{}} markers: {n}")
    if n == 0:
        print("  (the report was already unfilled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
