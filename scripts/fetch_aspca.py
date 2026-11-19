#!/usr/bin/env python3
"""
Data collection step 1 of 2 -- the ground-truth VETERINARY TOXICITY labels.

Source: ASPCA Animal Poison Control, "Toxic and Non-Toxic Plants"
        https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants

The site is a paginated list of ~1000 plants; every plant has its own detail
page that states, in a machine-readable sentence, which animals the plant is
toxic to, the toxic principle and the clinical signs.  This script

  1. downloads the index pages and builds {slug -> (common, scientific)},
  2. resolves every row of data/species_targets.csv against that index,
  3. downloads the detail page of every resolved plant,
  4. parses "Toxicity:", "Toxic Principles:" and "Clinical Signs:",
  5. writes data/raw/aspca_details.json.

Nothing is hand-written: every toxicity label in the database comes from a
page this script actually downloaded.

    python scripts/fetch_aspca.py

Raw HTML is cached in .cache/aspca/ so re-runs are free.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE = ROOT / ".cache" / "aspca"
RAW_OUT = ROOT / "data" / "raw" / "aspca_details.json"
BASE = "https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def curl(url: str, out: Path) -> bool:
    """Download a URL into `out` (cached)."""
    if out.exists() and out.stat().st_size > 2000:
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        res = subprocess.run(
            ["curl", "-sL", "--max-time", "60", "-A", UA, url, "-o", str(out),
             "-w", "%{http_code}"],
            capture_output=True, text=True,
        )
        if res.stdout.strip() == "200" and out.exists() and out.stat().st_size > 2000:
            return True
        time.sleep(2)
    return False


def build_index() -> dict[str, dict]:
    """Download the paginated index and return {slug: {common, scientific}}."""
    index_path = CACHE / "index.json"
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))

    rows_re = re.compile(
        r'<div class="views-row views-row-\d+[^"]*">(.*?)(?=<div class="views-row views-row-\d+|$)',
        re.S)
    name_re = re.compile(r'<div class="plant-title-name">(.*?)</div>', re.S)
    slug_re = re.compile(
        r'/pet-care/aspca-poison-control/toxic-and-non-toxic-plants/([a-z0-9\-]+)"')

    entries: dict[str, dict] = {}
    page = 0
    while True:
        f = CACHE / f"idx_{page}.html"
        if not curl(f"{BASE}?page={page}", f):
            break
        raw = f.read_text(encoding="utf-8", errors="replace")
        if len(rows_re.findall(raw)) == 0:
            break
        for m in rows_re.finditer(raw):
            block = m.group(1)
            names = [html.unescape(re.sub(r"\s+", " ", x)).strip()
                     for x in name_re.findall(block)]
            slugs = slug_re.findall(block)
            if not names or not slugs:
                continue
            entries.setdefault(slugs[0], {
                "common": names[0],
                "scientific": names[1] if len(names) > 1 else "",
            })
        if f'page={page + 1}' not in raw:
            break
        page += 1
        if page > 120:
            break
    index_path.write_text(json.dumps(entries, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(f"  index: {len(entries)} plants")
    return entries


def strip_html(raw: str) -> str:
    txt = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    return re.sub(r"\s+", " ", txt)


def parse_detail(raw: str) -> dict:
    txt = strip_html(raw)

    def field(label: str, stop_at: str = "") -> str:
        i = txt.find(label)
        if i < 0:
            return ""
        j = txt.find(stop_at, i) if stop_at else -1
        seg = txt[i + len(label): j if j > 0 else i + len(label) + 600]
        return seg.strip(" :\n\t")

    title = ""
    m = re.search(r"Toxic and Non-Toxic Plants ([A-Z][^|]{1,60}?) (?:Additional|Scientific|Toxicity)", txt)
    if m:
        title = m.group(1).strip()

    additional = field("Additional Common Names:", "Scientific Name:")
    scientific = field("Scientific Name:", "Family:")
    family = field("Family:", "Toxicity:")
    toxicity = field("Toxicity:", "Toxic Principles:")
    principles = field("Toxic Principles:", "Clinical Signs:")
    signs = field("Clinical Signs:", "If you suspect")

    # the page ends with a "Was this information helpful?" widget -- cut it off
    toxicity = toxicity.split("Was this")[0].strip(" ,")
    principles = principles.split("Was this")[0].strip(" ,")
    signs = signs.split("Was this")[0].strip(" ,")
    additional = additional.split("Was this")[0].strip(" ,")
    scientific = scientific.split("Was this")[0].strip(" ,")
    family = family.split("Was this")[0].strip(" ,")

    return {
        "title": title,
        "additional_common_names": additional.strip(),
        "scientific_name": scientific.strip(),
        "family": family.strip(),
        "toxicity": toxicity.strip(),
        "toxic_principles": principles.strip(),
        "clinical_signs": signs.strip(),
    }


def classify(toxicity: str) -> tuple[int | None, int | None]:
    """
    Map the ASPCA 'Toxicity:' sentence onto (toxic_to_cats, toxic_to_dogs).

    The sentence looks like "Toxic to Dogs, Non-Toxic to Cats" or
    "Non-Toxic to Cats, Non-Toxic to Dogs, Non-Toxic to Horses".  The
    "non-toxic to X" phrases are removed FIRST, otherwise the substring
    "toxic to cats" inside "non-toxic to cats" would invert the label.
    """
    t = (toxicity or "").lower()
    t = re.sub(r"non-?toxic to (cats|dogs|horses)", " ", t)
    cats = 1 if re.search(r"toxic to cats", t) else 0
    dogs = 1 if re.search(r"toxic to dogs", t) else 0
    return cats, dogs


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

    print("[1/3] building the ASPCA plant index ...")
    index = build_index()
    if not index:
        print("ERROR: could not download the ASPCA index")
        return 1

    import pandas as pd
    targets = pd.read_csv(ROOT / "data" / "species_targets.csv").fillna("")

    print(f"[2/3] resolving {len(targets)} target species against the index ...")
    resolved, unresolved = {}, []
    for _, row in targets.iterrows():
        qc = str(row["query_common"]).strip()
        qs = str(row["query_scientific"]).strip()
        cands = [(slug, v) for slug, v in index.items()
                 if v["common"].lower() == qc.lower()]
        if not cands:
            cands = [(slug, v) for slug, v in index.items()
                     if qc.lower() in v["common"].lower()]
        if qs:
            exact = [(s, v) for s, v in cands
                     if qs.lower() in v["scientific"].lower()
                     or v["scientific"].lower().startswith(qs.lower()[:12])]
            if exact:
                cands = exact
        if not cands:
            unresolved.append((qc, qs))
            continue
        resolved[qc] = cands[0][0]
    print(f"  resolved {len(resolved)}/{len(targets)}")
    if unresolved:
        print("  UNRESOLVED (need a manual check):")
        for qc, qs in unresolved:
            print(f"    - {qc} | {qs}")

    print("[3/3] downloading and parsing the plant detail pages ...")
    details = {}
    for i, (qc, slug) in enumerate(resolved.items(), 1):
        f = CACHE / f"detail_{slug}.html"
        if not curl(f"{BASE}/{slug}", f):
            print(f"  FAILED to download {qc}")
            continue
        parsed = parse_detail(f.read_text(encoding="utf-8", errors="replace"))
        cats, dogs = classify(parsed["toxicity"])
        parsed["slug"] = slug
        parsed["aspca_url"] = f"{BASE}/{slug}"
        parsed["toxic_to_cats"] = cats
        parsed["toxic_to_dogs"] = dogs
        parsed["aspca_common_name"] = index[slug]["common"]
        parsed["aspca_scientific_name"] = index[slug]["scientific"]
        details[qc] = parsed
        if i % 20 == 0:
            print(f"  {i}/{len(resolved)}")

    RAW_OUT.write_text(json.dumps(details, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    labelled = sum(1 for v in details.values()
                   if v["toxic_to_cats"] is not None and v["toxic_to_dogs"] is not None)
    print(f"  wrote {len(details)} records ({labelled} with a complete "
          f"cat+dog label) -> {RAW_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
