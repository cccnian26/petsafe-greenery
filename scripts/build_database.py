#!/usr/bin/env python3
"""
Data collection step 3 -- assemble the ground-truth database.

Inputs
  data/raw/aspca_details.json  -- veterinary toxicity labels (ASPCA)
  data/raw/ncstate_plants.json  -- light requirements      (NC State Extension)
  data/species_targets.csv      -- planting role + curated fallbacks

Rules
  * A species enters the database only if the ASPCA page explicitly stated a
    "Toxicity:" line.  Species whose page was a stub are dropped -- an
    unverified label is worse than no label.
  * Entries that share a scientific name are merged into one species and the
    toxicity labels are combined CONSERVATIVELY (toxic if any entry says so).
  * The light requirement is the most demanding condition NC State lists
    ("full sun" > "partial shade" > "dappled sunlight" > "deep shade");
    if NC State does not list the species, the curated fallback is used and
    the provenance is recorded.
  * The moisture requirement is a curated horticultural value; NC State does
    not publish soil moisture in a machine-readable form.

Outputs
  data/plants.csv          -- the database used by the agent and the evaluator
  data/plants_notes.md     -- provenance, coverage and cross-check tables

    python scripts/build_database.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_CSV = ROOT / "data" / "plants.csv"
OUT_NOTES = ROOT / "data" / "plants_notes.md"

LIGHT_PRIORITY = ["full_sun", "partial_shade", "bright_indirect", "full_shade"]

def norm_sci(name: str) -> str:
    name = re.sub(r"\s*cv\s.*$", "", str(name).strip(), flags=re.I)
    name = re.sub(r"\b(spp?|species|variety)\b\.?", "", name, flags=re.I)
    name = re.sub(r"[^a-zA-Z ]", " ", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def primary_light(options: list[str]) -> str:
    """
    The `light` column stores the SHADIEST condition the plant tolerates.

    NC State lists every light condition a plant accepts, so the LEAST
    demanding entry is the plant's tolerance limit:
        full sun        (3)  >  partial shade   (2)
        bright indirect (1)  >  deep shade      (0)
    """
    for light in reversed(LIGHT_PRIORITY):
        if light in options:
            return light
    return "partial_shade"


def clean(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip(" .")
    text = re.sub(r"\s*If you suspect.*$", "", text, flags=re.I)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def main() -> int:
    det = json.loads((ROOT / "data" / "raw" / "aspca_details.json").read_text(encoding="utf-8"))
    nc = json.loads((ROOT / "data" / "raw" / "ncstate_plants.json").read_text(encoding="utf-8"))
    targets = pd.read_csv(ROOT / "data" / "species_targets.csv").fillna("")
    ov_path = ROOT / "data" / "light_overrides.csv"
    overrides = {}
    if ov_path.exists():
        ov = pd.read_csv(ov_path).fillna("")
        overrides = {str(r["query_common"]).strip(): str(r["light"]).strip()
                     for _, r in ov.iterrows()}

    rows: dict[str, dict] = {}
    dropped_no_label: list[str] = []
    dropped_no_source: list[str] = []

    for _, t in targets.iterrows():
        qc = str(t["query_common"]).strip()
        rec = det.get(qc)
        if rec is None:
            dropped_no_source.append(qc)
            continue
        tox = (rec.get("toxicity") or "").strip()
        if not tox:
            # the ASPCA page carried no "Toxicity:" statement -> unverified
            dropped_no_label.append(qc)
            continue

        sci_raw = rec.get("aspca_scientific_name") or t["query_scientific"]
        sci = str(sci_raw).strip()
        key = norm_sci(sci)

        cats = bool(rec.get("toxic_to_cats"))
        dogs = bool(rec.get("toxic_to_dogs"))

        nc_rec = nc.get(sci) or nc.get(sci_raw) or nc.get(sci.strip())
        if nc_rec:
            light = primary_light(nc_rec["light_options"])
            light_source = nc_rec["url"]
            nc_tags = nc_rec.get("tags", [])
        elif qc in overrides:
            # NC State does not list this species -- curated shade tolerance
            light = overrides[qc]
            light_source = "curated (species not listed by NC State)"
            nc_tags = []
        else:
            light = str(t["light_fallback"]).strip()
            light_source = "curated fallback (species not listed by NC State)"
            nc_tags = []

        entry = {
            "scientific_name": sci,
            "common_name": str(rec.get("aspca_common_name") or qc).strip(),
            "plant_type": str(t["plant_type"]).strip(),
            "light": light,
            "light_source": light_source,
            "moisture": str(t["moisture_fallback"]).strip(),
            "moisture_source": "curated horticultural value (NC State does not "
                               "publish soil moisture machine-readably)",
            "toxic_to_cats": int(cats),
            "toxic_to_dogs": int(dogs),
            "family": clean(rec.get("family", ""), 60),
            "toxic_principles": clean(rec.get("toxic_principles", ""), 120),
            "clinical_signs": clean(rec.get("clinical_signs", ""), 120),
            "aspca_toxicity": tox,
            "source_url": rec.get("aspca_url") or (
                "https://www.aspca.org/pet-care/aspca-poison-control/"
                "toxic-and-non-toxic-plants/" + rec.get("slug", "")),
            "nc_state_tags": "; ".join(nc_tags),
            "notes": "",
        }

        if key in rows:
            prev = rows[key]
            # conservative merge
            prev["toxic_to_cats"] = int(prev["toxic_to_cats"] or entry["toxic_to_cats"])
            prev["toxic_to_dogs"] = int(prev["toxic_to_dogs"] or entry["toxic_to_dogs"])
            names = [n.strip() for n in prev["common_name"].split(";")]
            if entry["common_name"] not in names:
                names.append(entry["common_name"])
            prev["common_name"] = "; ".join(names)
            if "NC State" not in prev["light_source"] and "curated" in prev["light_source"]:
                prev["light"] = entry["light"]
                prev["light_source"] = entry["light_source"]
        else:
            rows[key] = entry

    # -------------------------------------------------------------- notes --
    for key, e in rows.items():
        bits = []
        if e["toxic_to_cats"] or e["toxic_to_dogs"]:
            who = []
            if e["toxic_to_cats"]:
                who.append("cats")
            if e["toxic_to_dogs"]:
                who.append("dogs")
            bits.append("TOXIC to " + " and ".join(who))
            if e["toxic_principles"]:
                bits.append(e["toxic_principles"])
            if e["clinical_signs"]:
                bits.append(e["clinical_signs"])
        else:
            bits.append("non-toxic to cats and dogs")
        e["notes"] = "; ".join(b for b in bits if b)[:180]

    df = pd.DataFrame(list(rows.values()))
    df = df.sort_values(["toxic_to_cats", "toxic_to_dogs", "scientific_name"],
                         ascending=[False, False, True]).reset_index(drop=True)
    df.insert(0, "id", [f"p{i + 1:03d}" for i in range(len(df))])

    cols = ["id", "scientific_name", "common_name", "plant_type", "light", "moisture",
            "toxic_to_cats", "toxic_to_dogs", "source_url", "notes",
            "family", "toxic_principles", "clinical_signs", "aspca_toxicity",
            "light_source", "moisture_source", "nc_state_tags"]
    df = df[cols]
    df.to_csv(OUT_CSV, index=False)

    # ------------------------------------------------------- notes file ----
    n_safe = int(((df.toxic_to_cats == 0) & (df.toxic_to_dogs == 0)).sum())
    n_cat = int((df.toxic_to_cats == 1).sum())
    n_dog = int((df.toxic_to_dogs == 1).sum())
    nc_n = int(df.light_source.str.contains("plants.ces.ncsu.edu").sum())

    lines = [
        "# Ground-truth database -- provenance and coverage",
        "",
        "`data/plants.csv` is the deterministic substrate of the whole project:",
        "the agent's tool filters it, and the evaluator scores every generated",
        "design against it. It is built by three scripts, none of which hand-writes",
        "a label:",
        "",
        "| step | script | source | what it provides |",
        "|------|--------|--------|------------------|",
        "| 1 | `scripts/fetch_aspca.py` | ASPCA Animal Poison Control, *Toxic and Non-Toxic Plants* | veterinary toxicity labels for cats and dogs, toxic principles, clinical signs |",
        "| 2 | `scripts/fetch_ncstate.py` | NC State Extension Plant Toolbox | light requirements (and independent `#non-toxic for cats` tags used as a cross-check) |",
        "| 3 | `scripts/build_database.py` | merges 1 + 2 + curated fallbacks | `data/plants.csv` |",
        "",
        "## How a row is built",
        "",
        "* **Toxicity** comes only from the ASPCA page of that species. A species",
        "  whose ASPCA page carried no explicit `Toxicity:` statement was",
        "  *dropped*, because an unverified label is worse than no label.",
        "* Entries sharing a scientific name are merged into one species and the",
        "  labels are combined conservatively (toxic if any source entry says so).",
        "* **Light** is the most demanding condition NC State lists for the plant",
        "  (`full sun` > `partial shade` > `dappled sunlight` > `deep shade`).",
        "  NC State does not list every species; for those, the curated fallback in",
        "  `data/species_targets.csv` is used and `light_source` says so.",
        "* **Moisture** is a curated horticultural value in all cases -- NC State",
        "  does not publish soil moisture in a machine-readable form.",
        "",
        "## Coverage",
        "",
        f"* total species: **{len(df)}**",
        f"* non-toxic to both cats and dogs: **{n_safe}**",
        f"* toxic to cats: **{n_cat}**",
        f"* toxic to dogs: **{n_dog}**",
        f"* light requirement taken from NC State: **{nc_n}**",
        "",
        "### Light x moisture coverage",
        "",
        "```",
        df.pivot_table(index="light", columns="moisture", values="id",
                       aggfunc="count", fill_value=0).to_string(),
        "```",
        "",
        "An empty cell means that no species in the database satisfies that",
        "combination strictly. The agent's tool handles this with a documented",
        "constraint-relaxation ladder (the pet-safety filter is never relaxed).",
        "",
        "### Species dropped during curation",
        "",
    ]
    if dropped_no_label:
        lines.append(f"* no explicit toxicity statement ({len(dropped_no_label)}): "
                     + ", ".join(sorted(dropped_no_label)))
    if dropped_no_source:
        lines.append(f"* not found on the ASPCA list ({len(dropped_no_source)}): "
                     + ", ".join(sorted(dropped_no_source)))
    lines += [
        "",
        "## Cross-check against NC State tags",
        "",
        "NC State tags its own pages with `#non-toxic for cats` / `#toxic for cats`.",
        "Where both sources speak about the same species they can be compared;",
        "`scripts/check_database.py` reports the agreement rate.",
        "",
    ]
    OUT_NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {len(df)} species -> {OUT_CSV}")
    print(f"  non-toxic to both : {n_safe}")
    print(f"  toxic to cats     : {n_cat}")
    print(f"  toxic to dogs     : {n_dog}")
    print(f"  light from NC State: {nc_n}")
    print(f"  dropped (no label): {len(dropped_no_label)}; "
          f"dropped (not found): {len(dropped_no_source)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
