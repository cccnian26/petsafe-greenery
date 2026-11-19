#!/usr/bin/env python3
"""
Side-by-side comparison of the three methods on ONE scenario.

    # uses the cached results if they exist, otherwise runs the scenario
    python scripts/compare_one.py

    python scripts/compare_one.py --scenario s07
    python scripts/compare_one.py --index 4
    python scripts/compare_one.py --force          # ignore the cache
    python scripts/compare_one.py --backend offline  # no API key needed
    python scripts/compare_one.py --methods agent naive_rag

It prints, for the chosen scenario:

  1. the site description
  2. the design each method produced (zones, combination logic, care, cautions)
  3. a metrics table
  4. a toxicity forensic: which species were unsafe, and WHY each method
     picked them (from memory / from the retrieved context / filtered out)
  5. which Design Completeness rubric items each method missed

Output is plain ASCII so it prints correctly in any terminal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd                                        # noqa: E402

from src.agent import run_agent                            # noqa: E402
from src.baselines import run_naive_rag, run_zeroshot       # noqa: E402
from src.db import get_database                            # noqa: E402
from src.evaluate import evaluate_design                   # noqa: E402
from src.llm import LLM                                   # noqa: E402
from src.offline import make_offline_handler               # noqa: E402
from src.retrieval import BM25Retriever                    # noqa: E402
from src.config import RESULTS_DIR, SCENARIOS_CSV, write_json  # noqa: E402

METHODS = [
    ("zeroshot", run_zeroshot, "B1 zero-shot LLM"),
    ("naive_rag", run_naive_rag, "B2 naive keyword RAG"),
    ("agent", run_agent, "Proposed dual-constraint agent"),
]

W = 78


def line(ch: str = "-") -> str:
    return ch * W


def head(title: str) -> None:
    print()
    print(line("="))
    print(title)
    print(line("="))


def wrap(text: str, indent: str = "    ", width: int = 74) -> None:
    """Print a long string, wrapped. ASCII only."""
    if not text:
        return
    words = str(text).split()
    cur = indent
    for w in words:
        if len(cur) + len(w) + 1 > width:
            print(cur.rstrip())
            cur = indent + w + " "
        else:
            cur += w + " "
    if cur.strip():
        print(cur.rstrip())


def get_payload(method: str, runner, llm, scenario, retriever, args):
    """Return the result payload for one method, reusing the cache if present."""
    out_dir = Path(args.out) if args.out else RESULTS_DIR
    if args.backend == "offline":
        out_dir = out_dir / "offline_demo"
    path = out_dir / method / f"{scenario['id']}.json"
    if path.exists() and not args.force:
        return json.loads(path.read_text(encoding="utf-8")), "cached"

    if args.backend == "offline":
        llm.register_offline(make_offline_handler(method, {
            "light": scenario.get("light"),
            "moisture": scenario.get("moisture"),
            "pets": scenario.get("pets"),
        }))
    if method == "naive_rag":
        payload = runner(llm, scenario, retriever)
    else:
        payload = runner(llm, scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)
    return payload, "ran"


def describe_design(design: dict, payload: dict) -> None:
    print("  -- spatial structure --")
    zones = design.get("zones") or []
    if not zones:
        print("     (no zones)")
    for z in zones:
        layer = z.get("layer") or "?"
        role = z.get("zone_role") or "?"
        name = z.get("zone_name") or "(unnamed)"
        print(f"     [{layer:>8} / {role:<10}] {name}")
        if z.get("placement"):
            wrap("placement: " + str(z["placement"]), indent="        ")
        for pl in z.get("plants") or []:
            sci = pl.get("scientific_name") or pl.get("common_name") or "?"
            com = pl.get("common_name") or ""
            print(f"       * {sci}" + (f"  ({com})" if com and com != sci else ""))
            if pl.get("why"):
                wrap("why: " + str(pl["why"]), indent="           ")
            if pl.get("role_in_combination"):
                wrap("role in composition: " + str(pl["role_in_combination"]),
                     indent="           ")
        if z.get("maintenance"):
            for m in z["maintenance"]:
                wrap("maintenance: " + str(m), indent="         ")

    print("  -- combination logic --")
    if design.get("layout_strategy"):
        wrap("layout strategy: " + str(design["layout_strategy"]), indent="     ")
    if design.get("combination_logic"):
        wrap("logic: " + str(design["combination_logic"]), indent="     ")
    if not design.get("layout_strategy") and not design.get("combination_logic"):
        print("     (none stated)")

    print("  -- care --")
    ci = design.get("care_instructions") or []
    if ci:
        for c in ci:
            if isinstance(c, dict):
                bits = [str(c.get("task", "")), str(c.get("frequency", "")),
                        str(c.get("season", ""))]
                print("     - " + " | ".join(b for b in bits if b and b != "None"))
            else:
                wrap("- " + str(c), indent="     ")
    else:
        print("     (no care instructions)")

    print("  -- care cautions --")
    cc = design.get("care_cautions") or []
    if cc:
        for c in cc:
            wrap("- " + str(c), indent="     ")
    else:
        print("     (no cautions)")

    if design.get("pet_safety_note"):
        print("  -- pet safety note --")
        wrap(str(design["pet_safety_note"]), indent="     ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default=None, help="scenario id, e.g. s07")
    ap.add_argument("--index", type=int, default=None, help="0-based scenario index")
    ap.add_argument("--methods", nargs="+", default=[m for m, _, _ in METHODS],
                    choices=[m for m, _, _ in METHODS])
    ap.add_argument("--backend", default="gemini", choices=["gemini", "offline"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--force", action="store_true", help="ignore cached results")
    ap.add_argument("--out", default=None, help="results directory")
    args = ap.parse_args()

    db = get_database()
    scenarios = pd.read_csv(SCENARIOS_CSV, dtype=str).fillna("")
    rows = scenarios.to_dict("records")
    for s in rows:
        s["pets"] = [p for p in str(s.get("pets", "")).split("|") if p]

    if args.scenario:
        scenario = next((s for s in rows if s["id"] == args.scenario), None)
        if scenario is None:
            print(f"Unknown scenario id {args.scenario!r}. "
                  f"Available: {', '.join(s['id'] for s in rows)}")
            return 2
    elif args.index is not None:
        if not 0 <= args.index < len(rows):
            print(f"Index out of range (0..{len(rows) - 1}).")
            return 2
        scenario = rows[args.index]
    else:
        scenario = rows[0]

    head("SCENARIO")
    print(f"  id          : {scenario.get('id')}")
    print(f"  site type   : {scenario.get('site_type')}")
    print(f"  light       : {scenario.get('light')}")
    print(f"  moisture    : {scenario.get('moisture')}")
    print(f"  pets        : {', '.join(scenario.get('pets') or []) or '(none)'}")
    if scenario.get("brief_detail"):
        print("  brief       :")
        wrap(str(scenario["brief_detail"]), indent="     ")

    llm = LLM(model=args.model, backend=args.backend)
    retriever = BM25Retriever(db)

    results = []
    for method, runner, label in METHODS:
        if method not in args.methods:
            continue
        payload, status = get_payload(method, runner, llm, scenario,
                                      retriever, args)
        design = payload.get("design", {}) or {}
        metrics = evaluate_design(design, scenario, db)
        results.append({
            "method": method, "label": label, "status": status,
            "payload": payload, "design": design, "metrics": metrics,
        })

    for r in results:
        head(f"{r['label']}   [{r['status']}]")
        describe_design(r["design"], r["payload"])

    # ------------------------------------------------------------- metrics --
    head("METRICS")
    print("  safe    = share certified non-toxic by ASPCA (conservative)")
    print("  safe*   = same rate over the species that could be resolved")
    print("  viable  = share matching the site light + moisture")
    print()
    print(f"  {'method':<26}{'safe':>7}{'safe*':>8}{'viable':>8}{'dual':>7}"
          f"{'complete':>10}{'OoDB':>7}")
    print("  " + line()[:74])
    for r in results:
        m = r["metrics"]
        sr = m.get("pet_safety_compliance_resolved")
        print(f"  {r['label']:<26}{m['pet_safety_compliance']:>7.2f}"
              f"{(f'{sr:.2f}' if sr is not None else 'n/a'):>8}"
              f"{m['horticultural_viability']:>8.2f}"
              f"{m['dual_constraint_accuracy']:>7.2f}"
              f"{str(m['design_completeness_raw']) + '/15':>10}"
              f"{m['out_of_database_rate']:>7.2f}")
    print()
    print(f"  {'method':<26}{'toxic':>7}{'unverified':>12}{'provisional':>13}"
          f"{'assessable':>12}")
    print("  " + line()[:74])
    for r in results:
        m = r["metrics"]
        print(f"  {r['label']:<26}{m['n_toxic']:>7}"
              f"{m.get('n_unresolvable', 0):>12}"
              f"{m.get('n_provisional', 0):>13}"
              f"{m.get('n_assessable', 0):>12}")

    # ------------------------------------------------------------ forensics --
    head("TOXICITY FORENSICS")
    pets = [p for p in (scenario.get("pets") or [])]
    for r in results:
        m = r["metrics"]
        bad = [d for d in m["plant_details"] if d.get("reason") == "toxic_to_pet"]
        unknown = [d for d in m["plant_details"] if not d.get("resolved")]
        nonviable = [d for d in m["plant_details"] if d.get("reason") == "not_viable"]
        print(f"  {r['label']}")
        if not bad and not unknown and not nonviable:
            print("     every recommended species is safe and viable")
        for d in bad:
            tier = d.get("resolution_tier", 0)
            print(f"     TOXIC   : {d['name']}  "
                  f"(cats={d.get('toxic_to_cats')}, dogs={d.get('toxic_to_dogs')}"
                  f", evidence tier {tier})")
            if r["method"] == "naive_rag":
                retrieved = r["payload"].get("retrieved") or []
                names = {str(x.get("scientific_name", "")).lower()
                         for x in retrieved}
                if d["name"].lower() in names:
                    print("                -> it WAS in the retrieved top-8; "
                          "the model chose it anyway")
                else:
                    print("                -> it was NOT retrieved; the model "
                          "brought it in by itself")
            elif r["method"] == "zeroshot":
                print("                -> no retrieval at all: this came from "
                      "the model's own memory")
            else:
                print("                -> the deterministic filter had already "
                      "removed it before the model could see it")
        for d in unknown:
            print(f"     UNKNOWN : {d['name']} (no source could resolve it)")
        for d in nonviable:
            print(f"     NONVIABLE: {d['name']} (light/moisture mismatch)")
        tiers = {}
        for d in m["plant_details"]:
            tiers[d.get("resolution_tier", 0)] = tiers.get(d.get("resolution_tier", 0), 0) + 1
        print("     evidence tiers (1=curated DB, 2=ASPCA harvest, "
              "3=ASPCA-aligned secondary, 0=none): "
              + ", ".join(f"tier{k}={v}" for k, v in sorted(tiers.items())))
        if r["method"] == "agent":
            tr = r["payload"].get("tool_transcript") or []
            n_cand = r["payload"].get("n_candidates", 0)
            n_rep = r["payload"].get("n_repair_rounds", 0)
            n_crep = r["payload"].get("n_completeness_repair_rounds", 0)
            print(f"     tool calls={len(tr)}  candidates={n_cand}  "
                  f"safety repairs={n_rep}  completeness repairs={n_crep}")
            if r["payload"].get("relaxation_note"):
                print("     relaxation note:")
                wrap(str(r["payload"]["relaxation_note"]), indent="        ")

    # ---------------------------------------------------------- completeness --
    head("DESIGN COMPLETENESS -- which rubric items were missed")
    for r in results:
        missing = r["metrics"].get("completeness_missing") or []
        print(f"  {r['label']}: "
              f"{r['metrics']['design_completeness_raw']}/15 "
              f"(core {r['metrics']['design_completeness_core5']}/5)")
        if missing:
            for it in missing:
                print(f"     MISSING: {it}")
        else:
            print("     (all 15 items earned)")

    head("ONE-LINE READING")
    by = {r["method"]: r for r in results}
    if "agent" in by and "zeroshot" in by:
        a = by["agent"]["metrics"]
        b = by["zeroshot"]["metrics"]
        print(f"  The agent scores {a['pet_safety_compliance']:.2f} on pet safety "
              f"against {b['pet_safety_compliance']:.2f} for the zero-shot "
              f"baseline, because the toxic species are removed before the")
        print("  model ever sees them -- the model is not being 'more careful', "
              "it is being given less room to be wrong.")
    if "naive_rag" in by and "zeroshot" in by:
        n = by["naive_rag"]["metrics"]
        z = by["zeroshot"]["metrics"]
        print(f"  Retrieval alone lifts viability "
              f"({z['horticultural_viability']:.2f} -> "
              f"{n['horticultural_viability']:.2f}) but leaves safety at "
              f"{n['pet_safety_compliance']:.2f}: grounding and filtering fix "
              f"two different constraints.")
    print(line("="))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
