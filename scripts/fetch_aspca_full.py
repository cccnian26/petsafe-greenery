#!/usr/bin/env python3
"""
Data collection -- FULL ASPCA harvest (all ~1000 listed plants).

Why this exists
---------------
The curated database (data/plants.csv) holds 150 species with light and
moisture resolved from NC State.  That is the agent's *candidate catalogue*.
It is NOT enough to score the baselines fairly: when a zero-shot LLM
recommends "Peace Lily" and that species is outside the 150, the evaluator
cannot certify it and has to count it as unsafe -- even though it is in fact
non-toxic.

So we harvest the *whole* ASPCA index, which is the veterinary authority
behind every toxicity label in this project, and store it as a separate
snapshot: data/raw/aspca_full.json  and  data/aspca_snapshot.json.

    python scripts/fetch_aspca_full.py            # resume / incremental
    python scripts/fetch_aspca_full.py --limit 50 # smoke test

Raw HTML is cached in .cache/aspca_full/, so re-runs are free and the run is
resumable.  Nothing here is hand-written: every verdict comes from a page
this script actually downloaded.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE = ROOT / ".cache" / "aspca_full"
RAW_OUT = ROOT / "data" / "raw" / "aspca_full.json"
SNAP_OUT = ROOT / "data" / "aspca_snapshot.json"
BASE = "https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# "Non-Toxic to Cats" / "Toxic to Cats" / "Toxic to Dogs" ...
TOX_SENTENCE = re.compile(
    r"(Toxic to (Cats|Dogs|Horses|Birds)|Non-Toxic to (Cats|Dogs|Horses|Birds))")


def curl(url: str, out: Path, tries: int = 4) -> bool:
    if out.exists() and out.stat().st_size > 2000:
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(tries):
        res = subprocess.run(
            ["curl", "-sL", "--max-time", "45", "--connect-timeout", "15",
             "-A", UA, url, "-o", str(out), "-w", "%{http_code}"],
            capture_output=True, text=True,
        )
        code = res.stdout.strip()
        if code == "200" and out.exists() and out.stat().st_size > 2000:
            return True
        if out.exists() and out.stat().st_size <= 2000:
            out.unlink(missing_ok=True)
        time.sleep(1.5 * (attempt + 1))
    return False


def strip_html(raw: str) -> str:
    txt = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    return re.sub(r"\s+", " ", txt)


def build_index() -> dict[str, dict]:
    """Paginate the index page; return {slug: {common, scientific}}."""
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
    while page <= 200:
        f = CACHE / f"idx_{page}.html"
        if not curl(f"{BASE}?page={page}", f):
            print(f"  index page {page}: download failed, stopping")
            break
        raw = f.read_text(encoding="utf-8", errors="replace")
        blocks = rows_re.findall(raw)
        if not blocks:
            break
        for block in blocks:
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
    index_path.write_text(json.dumps(entries, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(f"  index: {len(entries)} plants across {page + 1} pages")
    return entries


def parse_detail(raw: str) -> dict:
    """Extract the toxicity sentence and the scientific name from a page."""
    txt = strip_html(raw)
    scientific = ""
    i = txt.find("Scientific Name:")
    if i >= 0:
        scientific = txt[i + len("Scientific Name:"):i + len("Scientific Name:") + 120]
        scientific = scientific.split("Family:")[0].strip(" :\n\t")
        scientific = re.sub(r"\s+", " ", scientific)
    toxicity = ""
    i = txt.find("Toxicity:")
    if i >= 0:
        seg = txt[i + len("Toxicity:"): i + len("Toxicity:") + 400]
        seg = seg.split("Toxic Principles:")[0].split("Clinical Signs:")[0]
        toxicity = seg.split("Was this")[0].strip(" :\n\t")
    title = ""
    m = re.search(r"Toxic and Non-Toxic Plants ([A-Z][^|]{1,70}?) (?:Additional|Scientific|Toxicity)", txt)
    if m:
        title = m.group(1).strip()
    return {"title": title, "scientific_name": scientific,
            "toxicity_sentence": re.sub(r"\s+", " ", toxicity)}


def classify(sentence: str) -> dict:
    """
    Turn the ASPCA sentence into flags.

    'Non-Toxic to Dogs, Non-Toxic to Cats'  -> safe for both
    'Toxic to Cats, Non-Toxic to Dogs'      -> toxic to cats only

    The non-toxic phrases MUST be removed before matching, otherwise
    'Non-Toxic to Cats' reads as 'Toxic to Cats'.
    """
    s = sentence or ""
    non_tox = set(m.group(1).lower() for m in
                  re.finditer(r"Non-Toxic to (Cats|Dogs|Horses|Birds)", s, re.I))
    tox = set(m.group(1).lower() for m in
              re.finditer(r"(?<!Non-)Toxic to (Cats|Dogs|Horses|Birds)", s, re.I))
    # a plant can be listed as "Toxic to Dogs, Non-Toxic to Cats"
    tox_cats = "cats" in tox and "cats" not in non_tox
    tox_dogs = "dogs" in tox and "dogs" not in non_tox
    if tox_cats or tox_dogs:
        return {"toxic_to_cats": int(tox_cats), "toxic_to_dogs": int(tox_dogs),
                "verdict": "toxic"}
    if {"cats", "dogs"} <= non_tox:
        return {"toxic_to_cats": 0, "toxic_to_dogs": 0, "verdict": "non_toxic"}
    if non_tox:
        return {"toxic_to_cats": 0, "toxic_to_dogs": 0, "verdict": "non_toxic_partial"}
    # The ASPCA lists a plant under every animal it affects.  A page that
    # names only other animals (typically "Toxic to Horses") means the plant
    # is NOT listed as toxic to cats or dogs, so it is safe for them.
    if tox:
        return {"toxic_to_cats": 0, "toxic_to_dogs": 0,
                "verdict": "non_toxic_to_cats_and_dogs"}
    return {"toxic_to_cats": None, "toxic_to_dogs": None, "verdict": "unknown"}


def fetch_one(slug: str) -> tuple[str, dict | None]:
    f = CACHE / "pages" / f"{slug}.html"
    if not curl(f"{BASE}/{slug}", f):
        return slug, None
    rec = parse_detail(f.read_text(encoding="utf-8", errors="replace"))
    return slug, rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="only fetch N detail pages")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("Full ASPCA harvest")
    print("=" * 70)
    index = build_index()
    slugs = sorted(index)
    if args.limit:
        slugs = slugs[: args.limit]
    print(f"  detail pages to fetch: {len(slugs)}")

    done = 0
    failed: list[str] = []
    records: dict[str, dict] = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_one, s): s for s in slugs}
        for fut in as_completed(futures):
            slug, rec = fut.result()
            done += 1
            if rec is None:
                failed.append(slug)
                continue
            verdict = classify(rec["toxicity_sentence"])
            if verdict["verdict"] == "unknown":
                # a page without a readable Toxicity line is NOT guessed
                failed.append(slug)
                continue
            entry = dict(index.get(slug, {}))
            entry.update({
                "slug": slug,
                "aspca_common_name": rec["title"] or entry.get("common", ""),
                "aspca_scientific_name": rec["scientific_name"] or entry.get("scientific", ""),
                "toxicity_sentence": rec["toxicity_sentence"],
                "aspca_url": f"{BASE}/{slug}",
            })
            entry.update(verdict)
            records[slug] = entry
            if done % 50 == 0:
                print(f"    {done}/{len(slugs)}  "
                      f"({time.time() - t0:.0f}s, {len(records)} usable)")

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUT.write_text(json.dumps(records, indent=1, ensure_ascii=False),
                       encoding="utf-8")

    # the snapshot is what the evaluator reads: a deterministic, offline file
    snap = {}
    for slug, rec in records.items():
        for name in (rec.get("aspca_common_name"), rec.get("aspca_scientific_name")):
            if name:
                snap[name.strip().lower()] = {
                    "canonical": rec.get("aspca_scientific_name") or rec.get("aspca_common_name"),
                    "common_name": rec.get("aspca_common_name"),
                    "scientific_name": rec.get("aspca_scientific_name"),
                    "toxic_to_cats": rec["toxic_to_cats"],
                    "toxic_to_dogs": rec["toxic_to_dogs"],
                    "verdict": rec["verdict"],
                    "source": "ASPCA",
                    "source_url": rec["aspca_url"],
                }
    SNAP_OUT.write_text(json.dumps(snap, indent=1, ensure_ascii=False),
                        encoding="utf-8")

    print("=" * 70)
    print(f"  usable species      : {len(records)}")
    print(f"  unusable / failed   : {len(failed)}")
    print(f"  snapshot names      : {len(snap)}")
    print(f"  wrote               : {RAW_OUT}")
    print(f"  wrote               : {SNAP_OUT}")
    print("=" * 70)
    if failed:
        (CACHE / "failed.json").write_text(json.dumps(failed, indent=1),
                                           encoding="utf-8")
        print(f"  failed slugs saved to {CACHE / 'failed.json'} (re-run to retry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
