"""
The automated evaluation harness.

Every metric is computed by deterministic Python code against the same
ground-truth database that the agent's tool uses.  The evaluator is therefore
*independent of the method being evaluated* -- it never asks the model
whether it was right.

Metrics (all reported as a fraction in [0, 1]):

  pet_safety_compliance  -- share of recommended plants that are certified
                             non-toxic to every household pet.  Certification
                             requires ASPCA evidence (the curated catalogue or
                             the full ASPCA harvest), so a species nobody has
                             verified is never counted as safe.
  pet_safety_compliance_resolved
                         -- the same rate restricted to species that could be
                             resolved at all, with the ASPCA-aligned secondary
                             source admitted.  This is the metric that makes
                             the comparison fair to the baselines, which are
                             allowed to name species outside our catalogue.
  horticultural_viability -- share that match the site's light + moisture
  dual_constraint_accuracy -- share that satisfy BOTH at the same time
  design_completeness     -- rubric score for spatial zoning, combination
                             logic, care instructions and care cautions
  out_of_database_rate   -- share of recommended plants that are not in the
                             curated catalogue
  unresolvable_rate       -- share that no source at all can resolve

Species that a method names but that is not in the curated catalogue are NOT
silently counted as toxic: they are resolved through
``src.aspca_resolver`` (curated catalogue -> full ASPCA harvest ->
ASPCA-aligned secondary catalogue -> alias map) and every verdict keeps its
source and source URL, so the report can show exactly why a species was
judged safe or unsafe.
"""
from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from .aspca_resolver import SpeciesResolver, get_resolver
from .db import PlantDatabase, get_database, normalize_light, normalize_moisture, normalize_pets
from .rubric import MAX_CORE, MAX_RAW, score_design
from .schema import extract_plant_names


def completeness_score(design: dict):
    """Backwards-compatible wrapper around the operational rubric."""
    result = score_design(design)
    return result.normalised, result.checks


# ------------------------------------------------------------ evaluation ---
def _palette_diversity(records) -> dict:
    """Diversity of the recommended palette (K-means based).

    A palette of six plants from six families is a better answer than six
    plants of the same kind, and this measures it.  The clustering only
    uses the plants that are already in the design, so it never touches
    the safety filter.
    """
    try:
        from .clustering import diversity_index
        return diversity_index(records)
    except Exception:                                       # noqa: BLE001
        return {}


def evaluate_design(
    design: dict,
    scenario: dict,
    db: PlantDatabase | None = None,
    resolver: SpeciesResolver | None = None,
) -> dict[str, Any]:
    """
    Evaluate one design against the ground truth of one scenario.

    Species that are not in the curated catalogue are resolved through the
    three-tier resolver, so a baseline that names "Peace Lily" is judged on
    the evidence rather than counted as toxic by default.
    """
    db = db or get_database()
    resolver = resolver or get_resolver()
    pets = normalize_pets(scenario.get("pets", []))
    light = normalize_light(scenario.get("light", ""))
    moisture = normalize_moisture(scenario.get("moisture", ""))

    names = extract_plant_names(design)
    details = []
    n_toxic = n_nonviable = n_unresolvable = 0
    n_certified_safe = n_provisional_safe = 0
    n_viable = n_dual = n_assessable = 0
    n_certified = n_provisional = 0
    n_outside_catalogue = 0

    recommended_records = []
    for name in names:
        verdict = resolver.resolve(name)
        rec = db.resolve(name)
        if rec is not None:
            recommended_records.append(rec)

        # ---- toxicity, with the provenance of the evidence ------------- #
        if verdict.tier == 1 and rec is not None:
            toxic = db.is_toxic_for(rec, pets)
        elif verdict.toxic_to_cats is not None:
            toxic = any(
                (pet == "cat" and verdict.toxic_to_cats)
                or (pet == "dog" and verdict.toxic_to_dogs)
                for pet in pets
            )
        else:
            toxic = False

        certified = verdict.tier in (1, 2) and verdict.toxic_to_cats is not None
        provisional = verdict.tier == 3 and verdict.toxic_to_cats is not None

        # ---- horticultural viability, only where light/moisture exist --- #
        # rec_light / rec_moisture are reported for every plant, so they must
        # be defined on every path -- including the one where we know
        # nothing at all about the species.
        rec_light = rec_moisture = ""
        if rec is not None:
            viable = db.is_viable_for(rec, light, moisture)
            rec_light, rec_moisture = rec.light, rec.moisture
        elif verdict.light and verdict.moisture:
            # The species is outside the curated catalogue but the ASPCA
            # harvest or the ASPCA-aligned catalogue tells us what it needs.
            from .db import LIGHT_COMPATIBILITY, MOISTURE_COMPATIBILITY
            rec_light, rec_moisture = verdict.light, verdict.moisture
            viable = (rec_light in LIGHT_COMPATIBILITY.get(light, set())
                      and rec_moisture in MOISTURE_COMPATIBILITY.get(moisture, set()))
        else:
            viable = False
        assessable = bool(rec is not None or (verdict.light and verdict.moisture))

        safe = not toxic
        both = safe and viable

        n_toxic += int(toxic)
        n_nonviable += int(not viable)
        n_outside_catalogue += int(verdict.tier != 1)
        n_certified += int(certified)
        n_provisional += int(provisional)
        n_certified_safe += int(certified and safe)
        n_provisional_safe += int(provisional and safe)
        n_viable += int(viable)
        n_dual += int(both)
        n_assessable += int(assessable)
        if not verdict.resolved:
            n_unresolvable += 1

        details.append({
            "name": name,
            "resolved": verdict.resolved,
            "scientific_name": (rec.scientific_name if rec is not None
                                else verdict.canonical),
            "common_name": (rec.common_name if rec is not None
                            else verdict.canonical),
            "toxic_to_cats": verdict.toxic_to_cats,
            "toxic_to_dogs": verdict.toxic_to_dogs,
            "light": rec_light,
            "moisture": rec_moisture,
            "safe": safe,
            "viable": viable,
            "both": both,
            "certified": certified,
            "provisional": provisional,
            "assessable": assessable,
            "resolution_tier": verdict.tier,
            "resolution_source": verdict.source,
            "source_url": verdict.source_url,
            "reason": ("toxic_to_pet" if toxic
                       else ("not_in_database" if not verdict.resolved
                             else ("not_viable" if not viable else "ok"))),
        })

    n = len(names)
    n_resolved = n - n_unresolvable
    completeness = score_design(design)
    _diversity = _palette_diversity(recommended_records)
    row = {
        "scenario_id": scenario.get("id"),
        "pets": pets,
        "light": light,
        "moisture": moisture,
        "n_recommended": n,
        "n_safe": n_certified_safe,
        "n_certified_safe": n_certified_safe,
        "n_provisional_safe": n_provisional_safe,
        "n_certified": n_certified,
        "n_provisional": n_provisional,
        "n_toxic": n_toxic,
        "n_nonviable": n_nonviable,
        "n_unknown": n_unresolvable,
        "n_unresolvable": n_unresolvable,
        "n_outside_catalogue": n_outside_catalogue,
        "n_assessable": n_assessable,
        # -- conservative headline metrics: only ASPCA-certified species
        #    count as safe, and only species we can assess count as viable
        "pet_safety_compliance": round(n_certified_safe / n, 4) if n else 0.0,
        "horticultural_viability": round(n_viable / n, 4) if n else 0.0,
        "dual_constraint_accuracy": round(n_dual / n, 4) if n else 0.0,
        "out_of_database_rate": round(n_outside_catalogue / n, 4) if n else 0.0,
        # -- fair metrics: the same rates over the species we could judge
        "pet_safety_compliance_resolved": (
            round((n_certified_safe + n_provisional_safe) / n_resolved, 4)
            if n_resolved else None),
        "horticultural_viability_assessed": (
            round(n_viable / n_assessable, 4) if n_assessable else None),
        "dual_constraint_accuracy_assessed": (
            round(n_dual / n_assessable, 4) if n_assessable else None),
        "viability_coverage": round(n_assessable / n, 4) if n else 0.0,
        "unresolvable_rate": round(n_unresolvable / n, 4) if n else 0.0,
        "outside_catalogue_rate": round(n_outside_catalogue / n, 4) if n else 0.0,
        "design_success": int(n > 0),
        # -- how varied the palette is (unsupervised clustering)
        "palette_diversity": _diversity,
        "palette_n_families": _diversity.get("n_families", 0),
        "palette_n_types": _diversity.get("n_types", 0),
        "palette_n_clusters": _diversity.get("n_clusters", 0),
        "palette_cluster_coverage": round(
            float(_diversity.get("cluster_coverage", 0.0)), 4),
        "plant_details": details,
    }
    row.update(completeness.as_dict())
    row["completeness_checks"] = completeness.checks
    row["completeness_missing"] = completeness.missing
    row["completeness_dimension_scores"] = completeness.dimension_scores
    # per-dimension pass fractions, used by the dimension-level figure
    for dim, d in completeness.dimension_scores.items():
        row[f"dimfrac_{dim}"] = round(d["earned"] / d["max"], 4) if d["max"] else 0.0
    return row


def aggregate(rows: Iterable[dict]) -> pd.DataFrame:
    """Turn per-scenario metric rows into a tidy dataframe."""
    return pd.DataFrame(list(rows))


def _mean(df: pd.DataFrame, column: str):
    """Mean of a column, ignoring rows where the metric is undefined."""
    if column not in df.columns:
        return None
    vals = [v for v in df[column].tolist() if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarise(df: pd.DataFrame, method: str) -> dict:
    """Aggregate metrics for one method."""
    if df.empty:
        return {"method": method, "n_scenarios": 0}
    out = {
        "method": method,
        "n_scenarios": int(len(df)),
        "pet_safety_compliance": round(df["pet_safety_compliance"].mean(), 4),
        "horticultural_viability": round(df["horticultural_viability"].mean(), 4),
        "dual_constraint_accuracy": round(df["dual_constraint_accuracy"].mean(), 4),
        "design_completeness": round(df["design_completeness"].mean(), 4),
        "design_completeness_raw_mean": round(df["design_completeness_raw"].mean(), 2),
        "design_completeness_core5_mean": round(df["design_completeness_core5"].mean(), 2),
        "out_of_database_rate": round(df["out_of_database_rate"].mean(), 4),
        "pet_safety_compliance_resolved": _mean(df, "pet_safety_compliance_resolved"),
        "horticultural_viability_assessed": _mean(df, "horticultural_viability_assessed"),
        "dual_constraint_accuracy_assessed": _mean(df, "dual_constraint_accuracy_assessed"),
        "viability_coverage": round(df["viability_coverage"].mean(), 4) if "viability_coverage" in df else None,
        "unresolvable_rate": round(df["unresolvable_rate"].mean(), 4) if "unresolvable_rate" in df else None,
        "total_certified_safe": int(df["n_certified_safe"].sum()) if "n_certified_safe" in df else None,
        "total_provisional_safe": int(df["n_provisional_safe"].sum()) if "n_provisional_safe" in df else None,
        "design_success_rate": round(df["design_success"].mean(), 4) if "design_success" in df else None,
        "total_recommended_plants": int(df["n_recommended"].sum()),
        "total_toxic_recommendations": int(df["n_toxic"].sum()),
        "total_unknown_recommendations": int(df["n_unknown"].sum()),
        "total_outside_catalogue": int(df["n_outside_catalogue"].sum()) if "n_outside_catalogue" in df else None,
        "outside_catalogue_rate": round(df["outside_catalogue_rate"].mean(), 4) if "outside_catalogue_rate" in df else None,
        "mean_recommendations_per_design": round(df["n_recommended"].mean(), 2),
        "mean_seconds_per_design": round(df["mean_seconds"].mean(), 2) if "mean_seconds" in df else None,
    }
    # palette diversity: families, growth habits and cluster coverage
    for _key, _label in (("palette_n_families", "mean_families"),
                         ("palette_n_types", "mean_plant_types"),
                         ("palette_cluster_coverage", "mean_cluster_coverage")):
        if _key in df.columns:
            out[_label] = round(
                df[_key].apply(lambda v: float(v) if isinstance(v, (int, float))
                               else 0.0).mean(), 3)
    # mean number of missing rubric items (how incomplete a design is on average)
    if "completeness_missing" in df.columns:
        out["mean_missing_rubric_items"] = round(
            df["completeness_missing"].apply(lambda m: len(m) if isinstance(m, list) else 0).mean(), 2)
    return out


def breakdown(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Per-group breakdown (by pet configuration, by light class, ...)."""
    if df.empty:
        return df
    cols = ["pet_safety_compliance", "horticultural_viability",
            "dual_constraint_accuracy", "design_completeness"]
    return df.groupby(by)[cols].mean().round(4).reset_index()


def rubric_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-rubric-item pass rate per method.

    This is the table that shows *which* design knowledge each method is
    missing, which is the most informative view of the completeness metric.
    """
    from .rubric import RUBRIC_ITEMS

    frames = []
    for method, sub in df.groupby("method"):
        row = {"method": method}
        for item in RUBRIC_ITEMS:
            col = f"check_{item.id}"
            if col in sub.columns:
                row[f"{item.id} {item.item}"] = round(float(sub[col].mean()), 4)
        frames.append(row)
    return pd.DataFrame(frames)
