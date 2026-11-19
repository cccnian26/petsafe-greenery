#!/usr/bin/env python3
"""
Data collection -- the ASPCA-aligned secondary catalogue.

Source: Luminoid/plantfolio-common-plants  (GitHub)
        https://github.com/Luminoid/plantfolio-common-plants
        dist/common_plants.json  (v1.10.0, 980 records)

What this source IS
-------------------
Every record carries `plantToxicity` with the values nonToxic / mildlyToxic /
toxic / unknown.  The dataset documentation states that this field is
"ASPCA-aligned severity" and the v1.10.0 changelog records that "ASPCA
toxicity re-verified".  It is therefore *aligned with* the ASPCA, but it is
NOT the ASPCA: the dataset's own disclaimer says it "is not maintained by
horticultural or botanical professionals and may contain errors".

That is exactly why it is kept in a SEPARATE tier from the ASPCA harvest:

    tier 1  ASPCA detail pages          -> authoritative, primary
    tier 2  plantfolio-common-plants    -> ASPCA-aligned, secondary
    tier 3  alias map (this file too)   -> name normalisation only

The script writes

  data/raw/plantfolio_common_plants.json   the downloaded file, unchanged
  data/plantfolio_catalog.json             normalised lookup table
  data/plant_aliases.json                  free-text name -> canonical name

    python scripts/fetch_plantfolio.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

URL = ("https://cdn.jsdelivr.net/gh/Luminoid/plantfolio-common-plants@main/"
       "dist/common_plants.json")
RAW_OUT = ROOT / "data" / "raw" / "plantfolio_common_plants.json"
CAT_OUT = ROOT / "data" / "plantfolio_catalog.json"
ALIAS_OUT = ROOT / "data" / "plant_aliases.json"

# plantfolio light vocabulary -> the four light classes used in this project.
# Our `light` column means "the darkest light the plant tolerates", so the
# preferred light of plantfolio is mapped conservatively: a plant that wants
# full sun is not credited with tolerating shade.
LIGHT_MAP = {
    "outdoorFullSun": "full_sun",
    "strongDirect": "full_sun",
    "outdoorPartialSun": "partial_shade",
    "brightIndirect": "bright_indirect",
    "mediumIndirect": "bright_indirect",
    "lowIndirect": "full_shade",
    "outdoorShade": "full_shade",
}

# watering interval in days -> moisture class
def moisture_from_intervals(p: dict) -> str:
    """Average summer/spring interval in days -> low / moderate / high."""
    vals = [p.get(k) for k in ("springInterval", "summerInterval",
                               "fallInterval", "winterInterval")]
    vals = [v for v in vals if isinstance(v, (int, float)) and v > 0]
    if not vals:
        return "moderate"
    avg = sum(vals) / len(vals)
    if avg <= 5:
        return "high"
    if avg <= 11:
        return "moderate"
    return "low"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def download() -> list[dict]:
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    if not RAW_OUT.exists() or RAW_OUT.stat().st_size < 100000:
        for attempt in range(5):
            res = subprocess.run(
                ["curl", "-sL", "--max-time", "180", "--connect-timeout", "20",
                 "-A", "Mozilla/5.0", URL, "-o", str(RAW_OUT), "-w", "%{http_code}"],
                capture_output=True, text=True,
            )
            if res.stdout.strip() == "200" and RAW_OUT.stat().st_size > 100000:
                break
            print(f"  download attempt {attempt + 1} failed "
                  f"(code={res.stdout.strip()}); retrying")
            RAW_OUT.unlink(missing_ok=True)
            import time
            time.sleep(5)
    data = json.loads(RAW_OUT.read_text(encoding="utf-8"))
    return [x for x in data if isinstance(x, dict) and "typeName" in x]


def main() -> int:
    print("=" * 70)
    print("plantfolio-common-plants (ASPCA-aligned secondary source)")
    print("=" * 70)
    plants = download()
    print(f"  records downloaded : {len(plants)}")

    catalog: dict[str, dict] = {}
    aliases: dict[str, str] = {}

    for p in plants:
        name = (p.get("typeName") or "").strip()
        if not name:
            continue
        tox = p.get("plantToxicity")
        light = LIGHT_MAP.get(p.get("lightPreference") or "", "")
        moisture = moisture_from_intervals(p)

        rec = {
            "common_name": name,
            "scientific_names": [s.strip() for s in
                                 re.split(r",", str(p.get("commonExamples") or ""))
                                 if s.strip()][:6],
            "plant_toxicity": tox,
            "toxic_to_cats": 1 if tox in ("toxic", "mildlyToxic") else 0,
            "toxic_to_dogs": 1 if tox in ("toxic", "mildlyToxic") else 0,
            "toxicity_verified": bool(tox and tox != "unknown"),
            "light": light,
            "moisture": moisture,
            "category": p.get("category"),
            "description": (p.get("description") or "")[:400],
            "care_tips": (p.get("careTips") or "")[:600],
            "source": "plantfolio-common-plants v1.10.0 (ASPCA-aligned)",
            "source_url": ("https://github.com/Luminoid/plantfolio-common-plants"
                           "/blob/main/dist/common_plants.json"),
        }
        catalog[slug(name)] = rec

        # aliases: the genus name, every scientific example, and the
        # "also known as" names inside the description
        aliases[slug(name)] = name
        for s in rec["scientific_names"]:
            aliases.setdefault(slug(s), name)
        m = re.search(r"also known as:\s*([^.]+)\.", rec["description"], re.I)
        if m:
            for alias in re.split(r",|;", m.group(1)):
                a = alias.strip()
                if a and len(a) > 2:
                    aliases.setdefault(slug(a), name)

    CAT_OUT.write_text(json.dumps(catalog, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    ALIAS_OUT.write_text(json.dumps(aliases, indent=1, ensure_ascii=False),
                         encoding="utf-8")

    n_tox = sum(1 for r in catalog.values() if r["toxicity_verified"])
    n_unknown = sum(1 for r in catalog.values() if not r["toxicity_verified"])
    print(f"  catalogue entries  : {len(catalog)}")
    print(f"  toxicity known     : {n_tox}   unknown: {n_unknown}")
    print(f"  alias names        : {len(aliases)}")
    print(f"  wrote              : {RAW_OUT}")
    print(f"  wrote              : {CAT_OUT}")
    print(f"  wrote              : {ALIAS_OUT}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
