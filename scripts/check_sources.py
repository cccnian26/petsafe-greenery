#!/usr/bin/env python3
"""
Cross-check the two toxicity sources and report the coverage.

    python scripts/check_sources.py

Three questions, three answers:

  1. COVERAGE  -- how many species can each source resolve?
  2. AGREEMENT -- on the species both sources cover, do they agree about
                   toxicity?  This is the evidence that the ASPCA-aligned
                   secondary source does not distort the safety verdict.
  3. CATALOGUE -- does the curated 150-species catalogue agree with the full
                   ASPCA harvest?  A silent disagreement would mean our
                   primary labels are stale.

Exit code is non-zero if a source is missing entirely.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.aspca_resolver import SpeciesResolver, get_resolver  # noqa: E402
from src.config import write_json                           # noqa: E402
from src.db import get_database                              # noqa: E402


def main() -> int:
    db = get_database()
    r = get_resolver()

    print("=" * 70)
    print("SOURCE COVERAGE AND AGREEMENT")
    print("=" * 70)
    print(f"  tier 1  curated catalogue data/plants.csv      : {len(db):>5} species")
    print(f"  tier 2  full ASPCA harvest data/aspca_snapshot  : "
          f"{len(r.snapshot):>5} names")
    print(f"  tier 3  plantfolio-common-plants (ASPCA-aligned) : "
          f"{len(r.catalog):>5} names")
    print(f"  alias map data/plant_aliases.json              : "
          f"{len(r.aliases):>5} names")

    if not r.snapshot:
        print("\n  WARNING: the full ASPCA harvest is missing. Run")
        print("           python scripts/fetch_aspca_full.py")
    if not r.catalog:
        print("\n  WARNING: the secondary catalogue is missing. Run")
        print("           python scripts/fetch_plantfolio.py")

    # ------------------------------------------------------ tier 2 vs 3 ---
    ag = r.agreement()
    print()
    print("-" * 70)
    print("  AGREEMENT  tier 2 (ASPCA) vs tier 3 (ASPCA-aligned secondary)")
    print("-" * 70)
    if not ag["overlap"]:
        print("  no overlap yet (the ASPCA harvest may still be running)")
    else:
        print(f"  species covered by both : {ag['overlap']}")
        print(f"  identical verdict        : {ag['agree']} "
              f"({ag['agreement_rate'] * 100:.1f}%)")
        if ag["conflicts"]:
            print(f"  disagreements            : {len(ag['conflicts'])}")
            for c in ag["conflicts"][:15]:
                print(f"     {c['name']:<34} ASPCA cats={c['aspca']['cats']} "
                      f"dogs={c['aspca']['dogs']} | secondary "
                      f"cats={c['plantfolio']['cats']} dogs={c['plantfolio']['dogs']} "
                      f"({c['plantfolio']['severity']})")
        else:
            print("  no disagreements")

    # ------------------------------------------------------ tier 1 vs 2 ---
    print()
    print("-" * 70)
    print("  CONSISTENCY  curated catalogue vs full ASPCA harvest")
    print("-" * 70)
    checked = mismatch = 0
    bad: list[str] = []
    for rec in db.records:
        snap = r.snapshot.get(rec.scientific_name.strip().lower()) or \
            r.snapshot.get(rec.common_name.strip().lower())
        if not snap:
            continue
        checked += 1
        if bool(snap.get("toxic_to_cats")) != bool(rec.toxic_to_cats) or \
           bool(snap.get("toxic_to_dogs")) != bool(rec.toxic_to_dogs):
            mismatch += 1
            bad.append(f"{rec.scientific_name} ({rec.common_name})")
    print(f"  curated species also in the harvest : {checked}")
    print(f"  verdict mismatches                   : {mismatch}")
    for name in bad[:15]:
        print(f"     {name}")

    # -------------------------------------------------------- resolution ---
    print()
    print("-" * 70)
    print("  RESOLUTION SPOT CHECK")
    print("-" * 70)
    for probe in ("Peace Lily", "Boston Fern", "Snake Plant", "Monstera deliciosa",
                  "Aloe Vera", "Zz Plant", "Lobelia", "Lavender"):
        v = r.resolve(probe)
        state = ("safe" if v.certified_safe
                 else "TOXIC" if (v.toxic_to_cats or v.toxic_to_dogs)
                 else "unverified")
        print(f"  {probe:<22} -> tier {v.tier}  {state:<10} "
              f"{(v.canonical or '')[:34]:<34} {v.source[:40]}")

    out = ROOT / "data" / "source_agreement.json"
    write_json(out, {
        "coverage": {
            "curated_catalogue": len(db),
            "aspca_harvest_names": len(r.snapshot),
            "secondary_catalogue_names": len(r.catalog),
            "alias_names": len(r.aliases),
        },
        "agreement": {k: v for k, v in ag.items() if k != "conflicts"},
        "agreement_conflicts": ag["conflicts"][:50],
        "curated_vs_harvest": {"checked": checked, "mismatches": mismatch,
                               "examples": bad[:20]},
    }, indent=1)
    print()
    print(f"  wrote {out}")
    print("=" * 70)
    return 0 if (r.snapshot or r.catalog) else 1


if __name__ == "__main__":
    raise SystemExit(main())
