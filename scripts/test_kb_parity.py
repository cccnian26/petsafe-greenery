#!/usr/bin/env python3
"""Parity test: the Horn knowledge base and the production filter agree.

The agent's safety filter is ordinary Python (``src/db.py``).  The
knowledge base in ``src/kb.py`` states the same rules in Horn form and
derives the answer with forward chaining.  Both must give exactly the same
answer for every species and every scenario, otherwise the formal
description and the running system would disagree.

    python scripts/test_kb_parity.py

The test is offline and costs nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_database, normalize_light, normalize_moisture, normalize_pets  # noqa: E402
from src.kb import build_kb, kb_decide                                      # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def check(name: str, ok: bool) -> None:
    CHECKS.append((name, bool(ok)))


def main() -> int:
    db = get_database()
    records = db.records
    names = [r.common_name or r.scientific_name for r in records]

    # ---- every scenario of the benchmark ---------------------------------
    import pandas as pd

    scenarios = pd.read_csv(ROOT / "data" / "scenarios.csv", dtype=str).fillna("")
    mismatches = []
    levels = {}
    for _, row in scenarios.iterrows():
        pets = normalize_pets([p for p in str(row["pets"]).split("|") if p])
        light = normalize_light(row["light"])
        moisture = normalize_moisture(row["moisture"])

        # the knowledge base
        kb = build_kb(records, pets, light, moisture)
        decision = kb_decide(kb)
        kb_set = decision["candidates"]
        levels[row["id"]] = decision["level"]

        # the production filter, applied at the same relaxation level
        if decision["level"] == 0:
            prod = db.query(pets=pets, light=light, moisture=moisture,
                            limit=None, only_safe=True)
        elif decision["level"] == 1:
            prod = db.query(pets=pets, light=light, moisture=None,
                            limit=None, only_safe=True)
        else:
            prod = db.query(pets=pets, light=None, moisture=None,
                            limit=None, only_safe=True)
        prod_set = {r.common_name or r.scientific_name for r in prod}

        if kb_set != prod_set:
            only_kb = sorted(kb_set - prod_set)[:5]
            only_prod = sorted(prod_set - kb_set)[:5]
            mismatches.append((row["id"], only_kb, only_prod))

    check(f"the knowledge base agrees with the filter on all "
          f"{len(scenarios)} scenarios", not mismatches)

    # ---- the rules that must never be relaxed ---------------------------
    kb = build_kb(records, ["cat", "dog"], "full_shade", "low")
    decision = kb_decide(kb)
    toxic = {r.common_name or r.scientific_name for r in records
             if r.toxic_to_cats or r.toxic_to_dogs}
    check("no toxic species is ever a candidate",
          not (decision["candidates"] & toxic))

    # ---- the reasoning is auditable --------------------------------------
    kb = build_kb(records, ["cat"], "full_sun", "moderate")
    kb.forward_chain()
    fired = {t["rule"] for t in kb.trace}
    check("the safety rule is recorded in the trace", "safety-cat" in fired)
    check("the strict candidate rule is recorded", "strict-candidate" in fired)
    check("the trace explains every firing",
          all(t.get("comment") for t in kb.trace))

    # ---- the empty-pool fallback still works -----------------------------
    # Find a site where the strict query really finds nothing, then check
    # that the ladder relaxes the horticultural constraints -- and only
    # those.
    empty_case = None
    for light in ("full_sun", "partial_shade", "bright_indirect", "full_shade"):
        for moisture in ("low", "moderate", "high"):
            for pets in (["cat"], ["cat", "dog"]):
                if not db.query(pets=pets, light=light, moisture=moisture,
                                limit=None, only_safe=True):
                    empty_case = (pets, light, moisture)
                    break
            if empty_case:
                break
        if empty_case:
            break
    check("the benchmark contains a site with no strict match",
          empty_case is not None)
    if empty_case:
        pets, light, moisture = empty_case
        kb = build_kb(records, pets, light, moisture)
        decision = kb_decide(kb)
        check("a site with no match relaxes the horticultural constraints",
              decision["level"] >= 1)
        check("the relaxation never touches pet safety",
              not (decision["candidates"]
                   & {r.common_name or r.scientific_name for r in records
                      if r.toxic_to_cats or r.toxic_to_dogs}))

    print("=" * 70)
    print("KNOWLEDGE-BASE PARITY TEST")
    print("=" * 70)
    for name, ok in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    for sid, only_kb, only_prod in mismatches[:5]:
        print(f"    scenario {sid}: only in KB {only_kb} | only in filter {only_prod}")
    failed = [n for n, ok in CHECKS if not ok]
    print()
    if failed:
        print("FAILED:", failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
