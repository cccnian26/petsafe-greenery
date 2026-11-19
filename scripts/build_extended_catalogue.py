#!/usr/bin/env python3
"""
Build the EXTENDED catalogue (optional, larger agent candidate pool).

    python scripts/build_extended_catalogue.py

The curated catalogue data/plants.csv has 150 species and was resolved by
hand against the ASPCA and NC State.  The ASPCA indexes 1023 plants, and the
ASPCA-aligned secondary source adds another 980 names, so the agent can be
given a far larger pool without any label being guessed:

  * toxicity  -- from the ASPCA detail pages (tier 2), else from the
                 ASPCA-aligned secondary catalogue (tier 3, marked as such)
  * light     -- from the curated catalogue where available, else from the
                 secondary source's lightPreference, mapped conservatively
                 (a plant that wants full sun is not credited with tolerating
                 shade)
  * moisture  -- from the curated catalogue where available, else derived
                 from the secondary source's watering intervals in days
  * role      -- copied from the curated catalogue, else "other"

Use it with:

    set PETSAFE_DB_PATH=data/plants_extended.csv

The default run of the experiment still uses the curated 150, because that is
the catalogue whose light and moisture values were each checked by hand.
This script exists so that the "the agent is only safe because its pool is
small" objection can be answered empirically rather than rhetorically.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.aspca_resolver import SpeciesResolver, get_resolver  # noqa: E402
from src.db import get_database                              # noqa: E402
from src.config import DATA_DIR                              # noqa: E402

OUT = DATA_DIR / "plants_extended.csv"
CURATED = DATA_DIR / "plants.csv"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def main() -> int:
    db = get_database()
    resolver = get_resolver()
    curated = pd.read_csv(CURATED, dtype=str).fillna("")

    rows: dict[str, dict] = {}
    for rec in db.records:
        key = slug(rec.scientific_name)
        rows[key] = {
            "id": rec.id,
            "scientific_name": rec.scientific_name,
            "common_name": rec.common_name,
            "plant_type": rec.plant_type,
            "light": rec.light,
            "moisture": rec.moisture,
            "toxic_to_cats": int(bool(rec.toxic_to_cats)),
            "toxic_to_dogs": int(bool(rec.toxic_to_dogs)),
            "source_url": rec.source_url,
            "notes": (rec.notes or "")[:400],
            "family": "",
            "toxic_principles": "",
            "clinical_signs": "",
            "aspca_toxicity": "",
            "light_source": "NC State Extension Plant Toolbox",
            "moisture_source": "curated horticultural value",
            "nc_state_tags": "",
            "evidence_tier": 1,
            "provenance": "curated catalogue (ASPCA + NC State)",
        }

    # ---- tier 2: the full ASPCA harvest ------------------------------- #
    seen = set()
    for slug_key, snap in resolver.snapshot.items():
        sci = (snap.get("scientific_name") or snap.get("common_name") or "").strip()
        com = (snap.get("common_name") or "").strip()
        if not sci:
            continue
        key = slug(sci)
        if key in rows:
            continue
        cat = resolver.catalog.get(slug_key)
        light = (cat or {}).get("light") or ""
        moisture = (cat or {}).get("moisture") or ""
        rows[key] = {
            "id": "",
            "scientific_name": sci,
            "common_name": com or sci,
            "plant_type": "other",
            "light": light,
            "moisture": moisture,
            "toxic_to_cats": int(bool(snap.get("toxic_to_cats"))),
            "toxic_to_dogs": int(bool(snap.get("toxic_to_dogs"))),
            "source_url": snap.get("source_url") or "",
            "notes": "",
            "family": "",
            "toxic_principles": "",
            "clinical_signs": "",
            "aspca_toxicity": "",
            "light_source": ("plantfolio-common-plants lightPreference (ASPCA-aligned)"
                             if light else ""),
            "moisture_source": ("plantfolio watering intervals (ASPCA-aligned)"
                                if moisture else ""),
            "nc_state_tags": "",
            "evidence_tier": 2,
            "provenance": "ASPCA full harvest (authoritative)",
        }
        seen.add(key)

    # ---- tier 3: ASPCA-aligned secondary source ----------------------- #
    for key, cat in resolver.catalog.items():
        if not cat.get("toxicity_verified"):
            continue
        sci = (cat.get("scientific_names") or [cat.get("common_name")])[0]
        sci = re.sub(r"\s*\(.*", "", sci).strip()
        if not sci:
            continue
        rkey = slug(sci)
        if rkey in rows:
            continue
        rows[rkey] = {
            "id": "",
            "scientific_name": sci,
            "common_name": cat.get("common_name") or sci,
            "plant_type": "other",
            "light": cat.get("light") or "",
            "moisture": cat.get("moisture") or "",
            "toxic_to_cats": int(bool(cat.get("toxic_to_cats"))),
            "toxic_to_dogs": int(bool(cat.get("toxic_to_dogs"))),
            "source_url": cat.get("source_url") or "",
            "notes": (cat.get("description") or "")[:300],
            "family": "",
            "toxic_principles": "",
            "clinical_signs": "",
            "aspca_toxicity": f"plantfolio: {cat.get('plant_toxicity')}",
            "light_source": "plantfolio-common-plants lightPreference (ASPCA-aligned)",
            "moisture_source": "plantfolio watering intervals (ASPCA-aligned)",
            "nc_state_tags": "",
            "evidence_tier": 3,
            "provenance": "plantfolio-common-plants (ASPCA-aligned, secondary)",
        }

    # tidy: ids, empty strings, and a stable order
    df = pd.DataFrame(list(rows.values()))
    df["id"] = [f"e{i:04d}" for i in range(1, len(df) + 1)]
    df = df.fillna("")
    df = df.sort_values(["evidence_tier", "scientific_name"]).reset_index(drop=True)
    df.to_csv(OUT, index=False)

    n_safe = int(((df.toxic_to_cats == 0) & (df.toxic_to_dogs == 0)).sum())
    print("=" * 70)
    print("Extended catalogue")
    print("=" * 70)
    print(f"  total species        : {len(df)}")
    for tier, label in ((1, "tier 1 curated"), (2, "tier 2 ASPCA harvest"),
                         (3, "tier 3 ASPCA-aligned")):
        n = int((df.evidence_tier == tier).sum())
        print(f"  {label:<22}: {n}")
    print(f"  non-toxic to both    : {n_safe}")
    print(f"  with light data      : {int((df.light != '').sum())}")
    print(f"  with moisture data   : {int((df.moisture != '').sum())}")
    print(f"  wrote                : {OUT}")
    print()
    print("  use it with:  set PETSAFE_DB_PATH=data/plants_extended.csv")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
