"""
The deterministic tools that the agent is allowed to call.

`query_pet_safe_plants` is the safety-critical tool: it filters the ground
-truth database by (a) household pets and (b) microclimate.  The LLM never
decides whether a plant is safe -- it only decides *which* of the
already-verified candidates to put into the design.

`audit_palette` is the self-correction step: after the LLM has produced a
palette, the deterministic auditor re-checks every recommended species
against the database and reports violations.
"""
from __future__ import annotations

from typing import Any

from google.genai import types

from .config import DEFAULT_PALETTE_SIZE
from .db import (
    PlantDatabase,
    PlantRecord,
    get_database,
    normalize_light,
    normalize_moisture,
    normalize_pets,
)


# --------------------------------------------------------------------------
# Tool 1: the verified candidate pool
# --------------------------------------------------------------------------
def query_pet_safe_plants(
    pets: list[str],
    light: str,
    moisture: str,
    plant_type: str | None = None,
    limit: int = DEFAULT_PALETTE_SIZE,
) -> dict[str, Any]:
    """
    Query the verified botanical & toxicology database for plants that are
    non-toxic to every household pet AND horticulturally viable for the site.

    Args:
        pets: list of household pets, any of ["cat", "dog"]. Use [] only if the
            household has no pets.
        light: site light class: "full_sun", "partial_shade", "bright_indirect"
            or "full_shade".
        moisture: site moisture class: "low", "moderate" or "high".
        plant_type: optional filter, e.g. "hanging", "grass", "groundcover".
        limit: maximum number of candidates to return.
    """
    db = get_database()
    pets_n = normalize_pets(pets)
    light_n = normalize_light(light)
    moisture_n = normalize_moisture(moisture)

    # ---------------------------------------------------------------------
    # Constraint relaxation ladder.
    #
    # The *pet safety* constraint is never relaxed -- it is the whole point
    # of the system.  The horticultural constraints are relaxed only if, and
    # only if, the strict query returns nothing, and every relaxation is
    # reported back to the agent (and logged) so that it can tell the user
    # that the site is marginal for the requested conditions.
    #
    #   level 0 : strict   (light + moisture + pet safety)
    #   level 1 : moisture relaxed   (light + pet safety)
    #   level 2 : light and moisture relaxed (pet safety only)
    # ---------------------------------------------------------------------
    attempts = [
        (0, light_n, moisture_n),
        (1, light_n, None),
        (2, None, None),
    ]
    records: list = []
    relaxation = 0
    for level, lq, mq in attempts:
        records = db.query(
            pets=pets_n, light=lq, moisture=mq,
            plant_type=plant_type, limit=int(limit), only_safe=True,
        )
        if records:
            relaxation = level
            break

    return {
        "query": {
            "pets": pets_n, "light": light_n, "moisture": moisture_n,
            "plant_type": plant_type, "limit": int(limit),
        },
        "relaxation_level": relaxation,
        "relaxation_note": (
            "none" if relaxation == 0 else
            "moisture constraint relaxed because no species matched strictly"
            if relaxation == 1 else
            "light and moisture constraints relaxed because no species matched strictly"
        ),
        "pet_safety_filter": "applied (never relaxed)",
        "n_candidates": len(records),
        "candidates": [r.public_dict() for r in records],
    }


# --------------------------------------------------------------------------
# Tool 2: the deterministic auditor (self-correction loop)
# --------------------------------------------------------------------------
def audit_palette(recommended_plants: list[str], pets: list[str],
                  light: str, moisture: str) -> dict[str, Any]:
    """
    Re-check a proposed palette against the ground-truth database.

    Args:
        recommended_plants: plant names (scientific or common) chosen by the model.
        pets: the household pets.
        light: site light class.
        moisture: site moisture class.
    """
    db = get_database()
    checked, violations, unknown = [], [], []
    for name in recommended_plants:
        rec = db.resolve(name)
        if rec is None:
            unknown.append(name)
            continue
        toxic = db.is_toxic_for(rec, pets)
        viable = db.is_viable_for(rec, light, moisture)
        entry = {
            "requested_name": name,
            "scientific_name": rec.scientific_name,
            "common_name": rec.common_name,
            "pet_safe": not toxic,
            "horticulturally_viable": viable,
            "light": rec.light,
            "moisture": rec.moisture,
            "toxic_to_cats": rec.toxic_to_cats,
            "toxic_to_dogs": rec.toxic_to_dogs,
            "source_url": rec.source_url,
        }
        checked.append(entry)
        if toxic:
            violations.append({**entry, "violation": "toxic_to_pet"})
        elif not viable:
            violations.append({**entry, "violation": "not_viable_for_site"})
    return {
        "n_checked": len(checked),
        "checked": checked,
        "n_violations": len(violations),
        "violations": violations,
        "unknown_plants": unknown,
        "audit_passed": len(violations) == 0 and len(unknown) == 0,
    }


# --------------------------------------------------------------------------
# Gemini function-calling schema
# --------------------------------------------------------------------------
TOOL_DISPATCH: dict[str, Any] = {
    "query_pet_safe_plants": query_pet_safe_plants,
    "audit_palette": audit_palette,
}

QUERY_TOOL_DECLARATION = types.FunctionDeclaration(
    name="query_pet_safe_plants",
    description=(
        "Query the verified ground-truth botanical & veterinary-toxicology database. "
        "Returns ONLY species that are non-toxic to every listed household pet and "
        "that survive the specified sunlight and moisture conditions. "
        "This is the only source of plants you may use in the final design."
    ),
    parameters={
        "type": "object",
        "properties": {
            "pets": {
                "type": "array",
                "items": {"type": "string", "enum": ["cat", "dog"]},
                "description": "Household pets. Use [] if the household has no pets.",
            },
            "light": {
                "type": "string",
                "enum": ["full_sun", "partial_shade", "bright_indirect", "full_shade"],
                "description": "Direct sunlight class of the balcony or courtyard.",
            },
            "moisture": {
                "type": "string",
                "enum": ["low", "moderate", "high"],
                "description": "Available soil moisture class of the site.",
            },
            "plant_type": {
                "type": "string",
                "description": (
                    "Optional role filter, e.g. hanging, grass, groundcover, "
                    "succulent, shrub, perennial, herb, foliage, tree."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of candidates to return (default 8).",
            },
        },
        "required": ["pets", "light", "moisture"],
    },
)

AUDIT_TOOL_DECLARATION = types.FunctionDeclaration(
    name="audit_palette",
    description=(
        "Deterministic audit of a proposed plant palette. Re-checks every "
        "recommended species against the ground-truth database for pet toxicity "
        "and horticultural viability. Returns the list of violations."
    ),
    parameters={
        "type": "object",
        "properties": {
            "recommended_plants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Plant names chosen for the design.",
            },
            "pets": {
                "type": "array",
                "items": {"type": "string", "enum": ["cat", "dog"]},
            },
            "light": {"type": "string", "enum": ["full_sun", "partial_shade", "bright_indirect", "full_shade"]},
            "moisture": {"type": "string", "enum": ["low", "moderate", "high"]},
        },
        "required": ["recommended_plants", "pets", "light", "moisture"],
    },
)

ALL_TOOLS = [types.Tool(function_declarations=[QUERY_TOOL_DECLARATION])]


def run_tool(name: str, args: dict) -> Any:
    """Execute a tool by name with the arguments the model produced."""
    if name not in TOOL_DISPATCH:
        raise KeyError(f"unknown tool: {name}")
    clean = {k: v for k, v in (args or {}).items() if v is not None}
    return TOOL_DISPATCH[name](**clean)
