#!/usr/bin/env python3
"""Fill the measured numbers into the report.

    python scripts\\fill_report.py                       # newest real run
    python scripts\\fill_report.py --run deepseek__deepseek-v4.1-flash
    python scripts\\fill_report.py --check              # only report what is missing

The report keeps every measured number as a ``\\todo{}`` marker so that no
number can be typed by hand and drift away from the results.  This script
replaces those markers with the numbers of one run:

  * the headline table (safety, resolved safety, viability, dual, completeness,
    out-of-database rate),
  * the completeness table (zones A1--A3, care C2--C3, core score, missing items),
  * the footnote that explains the two safety numbers,
  * a *draft* analysis paragraph that states the four discussion points with
    the real numbers -- written as a draft, because the wording is the
    student's to own.

It also checks that the figures in ``figures/`` come from the same run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import RESULTS_DIR, list_runs                   # noqa: E402

TEX = ROOT / "report" / "report_skeleton.tex"
FIGURES_DIR = ROOT / "figures"

ROW_LABEL = {
    "zeroshot": "Baseline 1 (zero-shot)",
    "naive_rag": "Baseline 2 (naive RAG)",
    "agent": "\\textbf{Proposed (agent)}",
}
ORDER = ["zeroshot", "naive_rag", "agent"]
TODO = "\\todo{}"


def fmt(value: object, digits: int = 3) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "--"
    if pd.isna(f):
        return "--"
    return f"{f:.{digits}f}"


def get(row: pd.Series, *names: str, default: object = None) -> object:
    for n in names:
        if n in row.index and not pd.isna(row[n]):
            return row[n]
    return default


def legacy_run() -> dict | None:
    """The old flat layout: results/summary.csv next to results/<method>/."""
    summary = ROOT / "results" / "summary.csv"
    if not summary.is_file():
        return None
    model = ""
    usage = ROOT / "results" / "usage.json"
    if usage.is_file():
        try:
            model = json.loads(usage.read_text(encoding="utf-8")).get("model", "")
        except (OSError, ValueError):
            model = ""
    return {"name": "results (old flat layout)", "path": ROOT / "results",
            "backend": "", "model": model, "timestamp": "", "n_scenarios": 0,
            "legacy": True}


def pick_run(name: str | None) -> dict | None:
    if name:
        for r in list_runs():
            if r["name"] == name:
                return r
        return None
    runs = [r for r in list_runs() if not r.get("simulated")]
    if runs:
        return runs[0]
    return legacy_run()


def headline_rows(df: pd.DataFrame) -> dict[str, str]:
    """The three rows of the headline table, as LaTeX cell text."""
    out: dict[str, str] = {}
    for method in ORDER:
        sub = df[df["method"] == method]
        if sub.empty:
            out[method] = " \\todo{} & \\todo{} & \\todo{} & \\todo{} & \\todo{} & \\todo{} \\\\"
            continue
        r = sub.iloc[0]
        cells = [
            fmt(get(r, "pet_safety_compliance")),
            fmt(get(r, "pet_safety_compliance_resolved")),
            fmt(get(r, "horticultural_viability")),
            fmt(get(r, "dual_constraint_accuracy")),
            fmt(get(r, "design_completeness_raw_mean", default=0), 1),
            fmt(get(r, "outside_catalogue_rate")),
        ]
        out[method] = " & ".join(cells) + " \\\\"
    return out


def completeness_rows(df: pd.DataFrame, rb: pd.DataFrame | None) -> dict[str, str]:
    """The three rows of the completeness table.

    ``rb`` is the per-item pass-rate table (``rubric_breakdown.csv``): one
    column per rubric item, one row per method.  The share of scenarios
    that earned every item of a group is the mean of those columns.
    """
    out: dict[str, str] = {}
    for method in ORDER:
        sub = df[df["method"] == method]
        core = missing = None
        if not sub.empty:
            r = sub.iloc[0]
            core = fmt(get(r, "design_completeness_core5_mean", default=0), 1)
            missing = fmt(get(r, "mean_missing_rubric_items", default=0), 1)
        zones = _item_rate(rb, method, ["A1", "A2", "A3"])
        care = _item_rate(rb, method, ["C2", "C3"])
        if zones == "\\todo{}" or care == "\\todo{}":
            out[method] = " \\todo{} & \\todo{} &  & \\todo{} & \\todo{} \\\\"
            continue
        core_text = core if core else TODO
        missing_text = missing if missing else TODO
        out[method] = f"{zones} & {care} &  & {core_text} & {missing_text} \\\\"
    return out


def _item_rate(rb: pd.DataFrame | None, method: str,
               item_ids: list[str]) -> str:
    """The share of scenarios that earned every item of a group."""
    if rb is None or rb.empty:
        return "\\todo{}"
    sub = rb[rb["method"] == method]
    if sub.empty:
        return "\\todo{}"
    row = sub.iloc[0]
    values = []
    for item_id in item_ids:
        value = None
        for col in rb.columns:
            if str(col).startswith(item_id + " "):
                value = row[col]
                break
        if value is None or pd.isna(value):
            return "\\todo{}"
        values.append(float(value))
    return fmt(sum(values) / len(values), 2)


def draft_analysis(df: pd.DataFrame) -> str:
    """A draft of the discussion paragraph, with the real numbers in it.

    It is deliberately short: the wording is the student's to own, and the
    report has a hard page limit.
    """
    def row(method: str) -> pd.Series | None:
        sub = df[df["method"] == method]
        return None if sub.empty else sub.iloc[0]

    z, r, a = row("zeroshot"), row("naive_rag"), row("agent")
    if a is None:
        return ""
    parts = [
        f"(i) The agent's pet-safety compliance is exactly "
        f"{fmt(get(a, 'pet_safety_compliance'))} because the filter is "
        f"deterministic: the model is never offered an unsafe species, "
        f"rather than the model being \emph{{more careful}}.",
    ]
    if z is not None and r is not None:
        parts.append(
            f"(ii) The baselines' viability is competitive "
            f"({fmt(get(z, 'horticultural_viability'))}, "
            f"{fmt(get(r, 'horticultural_viability'))}) while their safety is "
            f"not ({fmt(get(z, 'pet_safety_compliance'))}, "
            f"{fmt(get(r, 'pet_safety_compliance'))}): the two constraint "
            f"families are independent, and grounding fixes only one of them.")
        parts.append(
            f"(iii) Retrieval alone barely moves the completeness score "
            f"({fmt(get(z, 'design_completeness_raw_mean', default=0), 1)} to "
            f"{fmt(get(r, 'design_completeness_raw_mean', default=0), 1)} out "
            f"of 15); negative filtering is what changes it "
            f"({fmt(get(a, 'design_completeness_raw_mean', default=0), 1)}).")
        parts.append(
            f"(iv) A concrete failure case: the zero-shot baseline produces "
            f"{fmt(get(z, 'total_toxic_recommendations', default=0), 0)} toxic "
            f"recommendations, each invisible to the user unless a "
            f"deterministic check looks for it.")
    return " ".join(parts)


def footnote_text(df: pd.DataFrame) -> str:
    a = df[df["method"] == "agent"]
    if a.empty:
        return ""
    r = a.iloc[0]
    # Only the part that follows the sentence already in the report is
    # replaced, so the footnote is not duplicated.
    return (f"The agent's two numbers are "
            f"{fmt(get(r, 'pet_safety_compliance'))} and "
            f"{fmt(get(r, 'pet_safety_compliance_resolved'))}; the difference "
            f"is the species that no source could certify, and it is "
            f"reported rather than hidden.")


def check_figures(run: dict) -> list[str]:
    """Warnings about figures that do not come from the chosen run."""
    warnings: list[str] = []
    manifest_path = FIGURES_DIR / "figures_manifest.json"
    if not manifest_path.is_file():
        return ["figures/figures_manifest.json is missing -- run "
                "scripts\\make_figures.py so that the figures can be traced "
                "to a run."]
    try:
        info = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["figures/figures_manifest.json cannot be read."]
    if info.get("simulated"):
        warnings.append(
            f"the figures in figures/ are SIMULATED "
            f"({info.get('run')}). Re-run scripts\\make_figures.py on the real "
            f"run before submitting.")
    if info.get("run") != run.get("name"):
        warnings.append(
            f"the figures belong to run '{info.get('run')}' "
            f"(model {info.get('model')}) but the numbers come from "
            f"'{run.get('name')}' (model {run.get('model')}). Re-run "
            f"scripts\\make_figures.py so that both belong to the same run.")
    referenced = set(re.findall(r"\\includegraphics\[[^]]*\]\{([^}]*)\}",
                                TEX.read_text(encoding="utf-8")))
    for ref in sorted(referenced):
        if not (FIGURES_DIR / ref).is_file():
            warnings.append(f"the report uses {ref} but figures/{ref} is missing.")
    return warnings


def main() -> int:
    p = argparse.ArgumentParser(description="fill the report with measured numbers")
    p.add_argument("--run", default=None, help="run folder (default: newest real run)")
    p.add_argument("--check", action="store_true",
                   help="only report what is missing, do not change the file")
    p.add_argument("--tex", default=str(TEX))
    args = p.parse_args()

    run = pick_run(args.run)
    if run is None:
        print("No experimental results found.")
        print("This script needs results/runs/<model>/summary.csv")
        print("(or results/summary.csv from the old flat layout).")
        print()
        print("Run the experiments once first -- this is FREE, because every")
        print("answer the model gave is already cached on disk:")
        print()
        print("    python scripts\\\\run_experiments.py --backend deepseek")
        print()
        print("Known runs:")
        for r in list_runs():
            print(f"  {r['name']}  ({r.get('model', '')})"
                  f"{'  [simulated]' if r.get('simulated') else ''}")
        if not list_runs():
            print("  (none)")
        print()
        print("跑完实验后，再执行：python scripts\\\\fill_report.py")
        return 1

    summary_path = Path(run["path"]) / "summary.csv"
    if not summary_path.is_file():
        print(f"No summary.csv in {run['path']}")
        return 1
    df = pd.read_csv(summary_path)
    print(f"run   : {run['name']}")
    print(f"model : {run.get('model', '')}")
    if run.get("legacy"):
        print("note : these results are in the old flat layout; run "
              "python scripts\\run_experiments.py once to move them into "
              "results/runs/<model>/ (free -- every answer is cached).")
    print(f"file  : {summary_path}")
    print()

    rb_path = Path(run["path"]) / "rubric_breakdown.csv"
    rb = None
    if rb_path.is_file():
        try:
            rb = pd.read_csv(rb_path)
        except (OSError, ValueError):
            rb = None
    else:
        print(f"  (no rubric_breakdown.csv in {run['path']})")

    head = headline_rows(df)
    comp = completeness_rows(df, rb)
    analysis = draft_analysis(df)
    foot = footnote_text(df)

    warnings = check_figures(run)
    for w in warnings:
        print(f"  !! {w}")
    print()

    if args.check:
        text = Path(args.tex).read_text(encoding="utf-8")
        n = text.count("\\todo{}")
        print(f"the report still contains {n} empty \\todo{{}} markers")
        return 0

    # The fill always starts from the pristine template, so filling again
    # with another model replaces the numbers instead of stacking on them.
    template = Path(args.tex).parent / "report_skeleton.template.tex"
    if template.is_file() and Path(args.tex).resolve() != template.resolve():
        text = template.read_text(encoding="utf-8")
        print(f"  starting from the template: {template.name}")
    else:
        text = Path(args.tex).read_text(encoding="utf-8")

    # --- headline table ------------------------------------------------
    for method in ORDER:
        pattern = re.compile(
            r"(" + re.escape(ROW_LABEL[method]) + r")\s*&[^\n]*?\\\\\s*\n")
        match = pattern.search(text)
        if not match:
            print(f"  (row not found: {ROW_LABEL[method]})")
            continue
        text = text[:match.start()] + f"{ROW_LABEL[method]} & {head[method]}\n" \
            + text[match.end():]

    # --- completeness table --------------------------------------------
    for method in ORDER:
        pattern = re.compile(
            r"(" + re.escape(ROW_LABEL[method]) + r")\s*&[^\n]*?\\\\\s*\n")
        # the completeness table comes second, so search after the first table
        matches = list(pattern.finditer(text))
        if len(matches) < 2:
            print(f"  (completeness row not found: {ROW_LABEL[method]})")
            continue
        m = matches[1]
        text = text[:m.start()] + f"{ROW_LABEL[method]} & {comp[method]}\n" \
            + text[m.end():]

    # --- footnote -------------------------------------------------------
    text = re.sub(r"\\todo\{Insert both and state the difference\s*\n?\s*"
                  r"explicitly in the text\.\}",
                  lambda _m: foot, text, flags=re.S)

    # --- analysis draft -------------------------------------------------
    if analysis:
        text = re.sub(r"\\todo\{Discuss:.*?\}", lambda _m: analysis,
                      text, flags=re.S)

    Path(args.tex).write_text(text, encoding="utf-8")
    left = text.count("\\todo{}")
    print(f"filled: {args.tex}")
    print(f"  empty \\todo{{}} markers left: {left}")
    print(f"  (the analysis paragraph is a DRAFT -- rewrite it in your own "
          f"words before submitting)")
    print()
    print("next:  python scripts\\make_figures.py     "
          "(if the figures are not from this run)")
    print("       python scripts\\build_report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
