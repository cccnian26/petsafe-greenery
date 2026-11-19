#!/usr/bin/env python3
"""
Data collection step 2 of 2 -- the HORTICULTURAL requirements.

Source: NC State Extension Plant Toolbox
        https://plants.ces.ncsu.edu/

For every species the toolbox states the light conditions the plant accepts
("Full sun", "Partial Shade", "Dappled Sunlight", "Deep shade").  Those are
mapped onto the controlled vocabulary used by the project:

    full sun        -> full_sun
    partial shade   -> partial_shade
    dappled sunlight-> bright_indirect
    deep shade      -> full_shade

The page also carries pet-toxicity tags ("#non-toxic for cats").  Those tags
are stored as an INDEPENDENT cross-check of the ASPCA labels, which is used
in the report to quantify how reliable the ground truth is.

    python scripts/fetch_ncstate.py

Raw HTML is cached in .cache/ncstate/.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE = ROOT / ".cache" / "ncstate"
RAW_OUT = ROOT / "data" / "raw" / "ncstate_plants.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

LIGHT_PRIORITY = [
    ("full sun", "full_sun"),
    ("partial shade", "partial_shade"),
    ("dappled sunlight", "bright_indirect"),
    ("deep shade", "full_shade"),
]


def curl(url: str, out: Path, min_size: int = 15000) -> bool:
    if out.exists() and out.stat().st_size > min_size:
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        res = subprocess.run(
            ["curl", "-sL", "--max-time", "60", "-A", UA, url, "-o", str(out),
             "-w", "%{http_code}"],
            capture_output=True, text=True,
        )
        if out.exists() and out.stat().st_size > min_size:
            return True
        time.sleep(2)
    return False


def text_of(raw: str) -> str:
    txt = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt


def parse_light(txt: str) -> list[str]:
    """Return every NC State light condition the plant accepts."""
    i = txt.find("Light:")
    if i < 0:
        return []
    seg = txt[i:i + 400].lower()
    found = []
    for needle, canonical in LIGHT_PRIORITY:
        if needle in seg:
            found.append(canonical)
    return found


def parse_tags(txt: str) -> list[str]:
    """Extract the '#non-toxic for X' style tags (cross-check source)."""
    tags = re.findall(r"#((?:non-?)?toxic for (?:cats|dogs|horses))", txt.lower())
    return sorted({t.replace("-", "") for t in tags})


def genus_slugs(genus: str) -> list[str]:
    """All NC State plant slugs that belong to a genus."""
    f = CACHE / f"genus_{genus}.html"
    curl(f"https://plants.ces.ncsu.edu/plants/genus/{genus.lower()}/", f)
    if not f.exists():
        return []
    raw = f.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(rf'/plants/({genus.lower()}-[a-z0-9\-]+)/', raw)))


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

    import pandas as pd
    det = json.loads((ROOT / "data" / "raw" / "aspca_details.json").read_text(encoding="utf-8"))
    targets = pd.read_csv(ROOT / "data" / "species_targets.csv").fillna("")

    sci_names: list[str] = []
    for qc in targets["query_common"]:
        rec = det.get(qc)
        sci = (rec or {}).get("aspca_scientific_name") or ""
        if sci and sci not in sci_names:
            sci_names.append(sci)
    genera = sorted({s.split()[0].lower() for s in sci_names if s.split()})

    print(f"[1/3] listing the NC State species of {len(genera)} genera ...")
    genus_map: dict[str, list[str]] = {}
    for g in genera:
        slugs = genus_slugs(g)
        if slugs:
            genus_map[g] = slugs
    print(f"  found {sum(len(v) for v in genus_map.values())} candidate species pages")

    print("[2/3] downloading the plant pages ...")
    wanted: dict[str, str] = {}   # slug -> scientific name
    for sci in sci_names:
        parts = sci.replace("cv", " ").replace("spp.", "").replace("sp.", "").split()
        if len(parts) < 2:
            continue
        genus, epithet = parts[0].lower(), re.sub(r"[^a-z0-9\-]", "", parts[1].lower())
        prefix = f"{genus}-{epithet}"
        slugs = genus_map.get(genus, [])
        exact = [s for s in slugs if s == prefix]
        if not exact:
            exact = [s for s in slugs if s.startswith(prefix)]
        if exact:
            wanted[exact[0]] = sci

    records: dict[str, dict] = {}
    for i, (slug, sci) in enumerate(wanted.items(), 1):
        f = CACHE / f"plant_{slug}.html"
        if not curl(f"https://plants.ces.ncsu.edu/plants/{slug}/", f):
            continue
        txt = text_of(f.read_text(encoding="utf-8", errors="replace"))
        lights = parse_light(txt)
        if not lights:
            continue
        records[sci] = {
            "slug": slug,
            "url": f"https://plants.ces.ncsu.edu/plants/{slug}/",
            "light_options": lights,
            "tags": parse_tags(txt),
        }
        if i % 30 == 0:
            print(f"  {i}/{len(wanted)}")

    # Second pass: species that the genus index did not list may still have a
    # page under the conventional "genus-species" slug.
    missing = []
    for sci in sci_names:
        if sci in records:
            continue
        parts = sci.replace("cv", " ").replace("spp.", "").replace("sp.", "").split()
        if len(parts) < 2:
            continue
        genus = parts[0].lower()
        epithet = re.sub(r"[^a-z0-9\-]", "", parts[1].lower())
        slug = f"{genus}-{epithet}"
        f = CACHE / f"plant_{slug}.html"
        if curl(f"https://plants.ces.ncsu.edu/plants/{slug}/", f, min_size=30000):
            txt = text_of(f.read_text(encoding="utf-8", errors="replace"))
            lights = parse_light(txt)
            if lights:
                records[sci] = {
                    "slug": slug,
                    "url": f"https://plants.ces.ncsu.edu/plants/{slug}/",
                    "light_options": lights,
                    "tags": parse_tags(txt),
                }
            else:
                missing.append(sci)
        else:
            missing.append(sci)
    if missing:
        print(f"  {len(missing)} species are not listed by NC State "
              f"(their light/moisture values come from the curated fallback)")

    RAW_OUT.write_text(json.dumps(records, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    print(f"[3/3] wrote {len(records)} NC State records -> {RAW_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
