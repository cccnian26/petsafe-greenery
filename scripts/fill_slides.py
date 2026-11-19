#!/usr/bin/env python3
"""Put the measured numbers into the presentation.

    python scripts\\fill_slides.py

The deck is patched directly (the .pptx is a zip of XML), so **Node.js is
not needed** and no extra Python package is installed.  It rewrites the
results table on slide 7 and the sentence below it, both of which otherwise
state whatever was typed by hand.

It also refreshes ``slides/data/results.json`` so that the deck can
rebuilt from source with Node.js if that is preferred:

    python scripts\\make_slide_data.py
    cd slides && node compile.js
"""
from __future__ import annotations

import argparse
import re
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.config import list_runs                             # noqa: E402

DEFAULT_PPTX = ROOT / "docs" / "PetSafe-Greenery-presentation.pptx"
SLIDE = 7
ORDER = ["zeroshot", "naive_rag", "agent"]
LABEL = {"zeroshot": "B1 zero-shot", "naive_rag": "B2 naive RAG",
         "agent": "Proposed agent"}


def legacy_run() -> dict | None:
    """The old flat layout: results/summary.csv next to results/<method>/.

    Results produced before the per-model folders existed still count, so
    they are accepted -- with a note that the runner will move them.
    """
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


def numbers(summary: pd.DataFrame) -> dict[str, list[str]]:
    """The five table cells of each method, in display order."""
    out: dict[str, list[str]] = {}
    for method in ORDER:
        sub = summary[summary["method"] == method]
        if sub.empty:
            out[method] = ["--"] * 5
            continue
        r = sub.iloc[0]

        def val(*names: str, default: float = 0.0) -> float:
            for n in names:
                if n in r.index and not pd.isna(r[n]):
                    return float(r[n])
            return default

        # Two decimals: the columns of the slide are narrow, and four
        # characters are all that fit without the numbers touching.
        out[method] = [
            f"{val('pet_safety_compliance'):.2f}",
            f"{val('horticultural_viability'):.2f}",
            f"{val('dual_constraint_accuracy'):.2f}",
            f"{val('design_completeness_raw_mean'):.1f}",
            f"{val('outside_catalogue_rate'):.2f}",
        ]
    return out


def finding(summary: pd.DataFrame) -> str:
    """The sentence under the table -- it must match the measured number."""
    sub = summary[summary["method"] == "agent"]
    if sub.empty:
        return ""
    row = sub.iloc[0]
    value = float(row.get("pet_safety_compliance", 0) or 0)
    pct = "100%" if abs(value - 1.0) < 1e-9 else f"{value * 100:.1f}%"
    return (f"The agent's pet-safety compliance is exactly {pct}, because the "
            f"filter is deterministic -- the model is never given the "
            f"opportunity to pick an unsafe species.")


def source_note(run: dict, n_scenarios: int) -> str:
    model = run.get("model", "?")
    return f"Source: {model}, {n_scenarios} scenarios"


def patch_pptx(pptx: Path, cells: dict[str, list[str]], note: str,
               finding_text: str) -> list[str]:
    """Rewrite the table cells and the sentences of slide 7, in place."""
    if not pptx.is_file():
        raise FileNotFoundError(pptx)

    with zipfile.ZipFile(pptx) as zf:
        entries = {name: zf.read(name) for name in zf.namelist()}

    slide_name = f"ppt/slides/slide{SLIDE}.xml"
    if slide_name not in entries:
        raise RuntimeError(f"{slide_name} not found in {pptx.name}")
    xml = entries[slide_name].decode("utf-8")

    # every text run, with its position in the XML
    matches = list(re.finditer(r"<a:t>([^<]*)</a:t>", xml))
    texts = [m.group(1) for m in matches]

    def index_of(predicate) -> int | None:
        for i, t in enumerate(texts):
            if predicate(t):
                return i
        return None

    changes: list[str] = []
    new_values: dict[int, str] = {}

    for method in ORDER:
        start = index_of(lambda t, m=method: t.strip() == LABEL[m])
        if start is None:
            raise RuntimeError(f"row '{LABEL[method]}' not found on slide {SLIDE}")
        for offset, value in enumerate(cells[method], start=1):
            new_values[start + offset] = value
        changes.append(f"{LABEL[method]}: " + " / ".join(cells[method]))

    # the source line under the table
    src_idx = index_of(lambda t: t.startswith("Fill from results/")
                       or t.startswith("Source:"))
    if src_idx is not None:
        new_values[src_idx] = note

    # the finding sentence
    find_idx = index_of(lambda t: "pet-safety compliance is exactly" in t)
    if find_idx is not None and finding_text:
        new_values[find_idx] = finding_text

    if not new_values:
        raise RuntimeError("nothing to patch")

    # replace from the end, so the offsets stay valid
    out = xml
    for i in sorted(new_values, reverse=True):
        m = matches[i]
        text = new_values[i]
        escaped = (text.replace("&", "&amp;").replace("<", "&lt;")
                   .replace(">", "&gt;"))
        out = out[:m.start(1)] + escaped + out[m.end(1):]

    entries[slide_name] = out.encode("utf-8")

    # ------------------------------------------------------------------
    # Replace the embedded figures with the current ones.
    #
    # The picture on a slide is a *copy* inside the .pptx, so regenerating
    # figures/ does not change the deck.  The copy is found by its content
    # hash, which is how it is identified in the first place.
    # ------------------------------------------------------------------
    figures_dir = ROOT / "figures"
    replaced: list[str] = []
    unknown: list[str] = []
    if figures_dir.is_dir():
        current = {}
        for fp in figures_dir.glob("*.png"):
            current.setdefault(hashlib.sha256(fp.read_bytes()).hexdigest(), fp)
        # Which embedded picture belongs to which figure?  The manifest
        # records it; a picture that still has the same content is matched
        # directly, which keeps the manifest up to date.
        manifest_path = ROOT / "docs" / "deck_figures.json"
        manifest: dict[str, str] = {}
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifest = {}
        for name in list(entries):
            if not (name.startswith("ppt/media/") and name.endswith(".png")):
                continue
            digest = hashlib.sha256(entries[name]).hexdigest()
            figure_name = manifest.get(name)
            if digest in current:
                # still identical: remember the mapping and leave it alone
                manifest[name] = current[digest].name
                continue
            if figure_name is None:
                unknown.append(name)
                continue
            source = figures_dir / figure_name
            if not source.is_file():
                unknown.append(f"{name} ({figure_name} missing)")
                continue
            entries[name] = source.read_bytes()
            replaced.append(f"{name} <- {figure_name}")
        if manifest:
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                                     encoding="utf-8")

    tmp = pptx.with_suffix(".pptx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    shutil.move(str(tmp), str(pptx))
    return changes, replaced, unknown


def main() -> int:
    p = argparse.ArgumentParser(description="fill the slides with the results")
    p.add_argument("--run", default=None, help="run folder (default: newest real run)")
    p.add_argument("--pptx", default=str(DEFAULT_PPTX))
    p.add_argument("--json", action="store_true",
                   help="also refresh slides/data/results.json")
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
        print("跑完实验后，再执行：python scripts\\\\fill_slides.py")
        return 1

    summary_path = Path(run["path"]) / "summary.csv"
    if not summary_path.is_file():
        print(f"No summary.csv in {run['path']}")
        return 1
    summary = pd.read_csv(summary_path)

    cells = numbers(summary)
    n_scen = int(summary["n_scenarios"].max()) if "n_scenarios" in summary \
        else 0
    note = source_note(run, n_scen)
    finding_text = finding(summary)

    pptx = Path(args.pptx)
    changes, replaced, unknown = patch_pptx(pptx, cells, note, finding_text)

    print(f"run  : {run['name']}")
    print(f"model: {run.get('model', '')}")
    if run.get("legacy"):
        print("note: these results are in the old flat layout. Run")
        print("      python scripts\\run_experiments.py --backend deepseek")
        print("      once to move them into results/runs/<model>/ (free: every")
        print("      answer is already cached).")
    for c in changes:
        print(f"  {c}")
    print(f"  note: {note}")
    print(f"updated: {pptx}")
    print("  (this is the file you open in PowerPoint: "
          "docs\\PetSafe-Greenery-presentation.pptx)")
    if replaced:
        print("  figures replaced (same picture, new file):")
        for r in replaced:
            print(f"    {r}")
    else:
        print("  figures: no change needed (already up to date)")
    for u in unknown:
        print(f"  ?? embedded picture {u} could not be matched to a file in "
              f"figures/ -- rebuild the deck with Node.js if it looks wrong")

    if args.json:
        import make_slide_data

        data = make_slide_data.build(Path(run["path"]))
        out = ROOT / "slides" / "data" / "results.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(__import__("json").dumps(data, indent=2,
                                                 ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"updated: {out}")

    print()
    print("Open the .pptx and check that the numbers on slide 7 are the ones")
    print("you expect.  If you rebuild the deck from source, run:")
    print("    python scripts\\make_slide_data.py")
    print("    cd slides && node compile.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
