"""
The structured output schema shared by ALL THREE evaluated methods.

Using one schema for the agent and for both baselines is what makes the
comparison in the report fair: the evaluator reads exactly the same fields
regardless of which method produced the design.

The schema deliberately forces the three things that make a planting scheme
actually usable -- and not just a list of plants:

  * HOW THE PLANTS GO TOGETHER  -> `layout_strategy`, `combination_logic`,
    `role_in_combination` per plant
  * HOW TO LOOK AFTER THEM        -> `maintenance` per zone, `care_instructions`
    (task + frequency + season)
  * WHAT CAN GO WRONG             -> `care_cautions`
"""
from __future__ import annotations

import json
import re

# The spatial taxonomy the agent is asked to use.  They are NOT enforced as
# JSON-schema enums (a hard enum makes the API reject an otherwise valid
# answer); they are instead the vocabulary the completeness rubric looks for.
ZONE_ROLES = [
    "hanging",       # trailing / railing / overhead
    "grazing",       # pet-accessible sensory or edible area
    "groundcover",   # low layer at floor level
    "focal",         # one feature plant in a container
    "edible",        # herbs and edibles
    "screening",     # privacy / wind screen
    "seasonal",      # plants for a particular season
    "succession",    # staged succession across the year
]
LAYERS = ["vertical", "mid", "ground"]

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "site_summary": {
            "type": "string",
            "description": "One sentence restating the microclimate and pet situation.",
        },
        "layout_strategy": {
            "type": "string",
            "description": (
                "How the scheme is SPATIALLY STRUCTURED: which vertical, mid and "
                "ground layers exist and how they stack (for example 'trailing "
                "plants on the railing at eye level, upright perennials at mid "
                "height against the wall, and a low ground layer along the "
                "balcony edge')."
            ),
        },
        "combination_logic": {
            "type": "string",
            "description": (
                "Why THESE plants work TOGETHER: contrast in height, texture, "
                "colour, growth habit and seasonal rhythm, and how the "
                "combination changes across the year."
            ),
        },
        "zones": {
            "type": "array",
            "description": "Spatial zones of the planting design (2-4 zones).",
            "items": {
                "type": "object",
                "properties": {
                    "zone_name": {"type": "string"},
                    "zone_role": {
                        "type": "string",
                        "description": (
                            "One of: " + ", ".join(ZONE_ROLES) +
                            ". The role describes what the zone does in the "
                            "scheme, not just which plants sit in it."
                        ),
                    },
                    "layer": {
                        "type": "string",
                        "description": (
                            "The height layer of this zone: 'vertical' "
                            "(hanging / above eye level), 'mid' (container level, "
                            "roughly knee to waist height) or 'ground' (floor "
                            "level, walkable edges)."
                        ),
                    },
                    "placement": {
                        "type": "string",
                        "description": (
                            "Where exactly the zone goes, INCLUDING ITS LIGHT "
                            "POSITION (e.g. 'on the east-facing railing, 3 h of "
                            "morning sun, sheltered from the afternoon heat')."
                        ),
                    },
                    "plants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scientific_name": {"type": "string"},
                                "common_name": {"type": "string"},
                                "why": {
                                    "type": "string",
                                    "description": "Why this plant fits this zone.",
                                },
                                "role_in_combination": {
                                    "type": "string",
                                    "description": (
                                        "What this plant CONTRIBUTES to the "
                                        "overall composition (height, texture, "
                                        "colour, scent, seasonal accent, ground "
                                        "cover) and how it interacts with the "
                                        "other plants in the zone."
                                    ),
                                },
                            },
                            "required": ["scientific_name", "common_name", "why",
                                         "role_in_combination"],
                        },
                    },
                    "maintenance": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Zone-specific care: watering for this zone, feeding, "
                            "pruning, deadheading, repotting."
                        ),
                    },
                },
                "required": ["zone_name", "zone_role", "layer", "placement",
                             "plants", "maintenance"],
            },
        },
        "care_instructions": {
            "type": "array",
            "description": (
                "Practical, site-wide care. Every entry must state WHAT to do, "
                "HOW OFTEN, and in which SEASON it matters."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "frequency": {
                        "type": "string",
                        "description": (
                            "How often, e.g. 'twice a week in summer, weekly in "
                            "spring and autumn'."
                        ),
                    },
                    "season": {
                        "type": "string",
                        "description": "Season or time of year this applies to.",
                    },
                },
                "required": ["task", "frequency", "season"],
            },
        },
        "care_cautions": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Cautions: what can go wrong with this specific scheme "
                "(overwatering and root rot in the hanging baskets, frost "
                "exposure of the tender perennials, a plant the pet will chew, "
                "scorch on the hot west wall, poor drainage in the corner "
                "pot). At least two entries, each specific to this design."
            ),
        },
        "pet_safety_note": {
            "type": "string",
            "description": "How the design keeps the pet safe (one or two sentences).",
        },
    },
    "required": ["site_summary", "layout_strategy", "combination_logic", "zones",
                 "care_instructions", "care_cautions", "pet_safety_note"],
}


def parse_json(text: str) -> dict:
    """
    Turn whatever the model returned into a dict.

    Handles: raw JSON, ```json fenced JSON, and JSON with a stray prefix or
    suffix (models sometimes add a sentence before or after the object).
    """
    if not text:
        return {}
    text = text.strip()

    # 1) fenced block
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()

    # 2) raw parse
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 3) first balanced {...} block
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return {}


def extract_plant_names(design: dict) -> list[str]:
    """
    Pull every plant name out of a design, in document order.

    We look at both `scientific_name` and `common_name` so that a model that
    only fills one of the two fields is still credited for naming the plant.
    """
    names: list[str] = []
    for zone in design.get("zones", []) or []:
        if not isinstance(zone, dict):
            continue
        for plant in zone.get("plants", []) or []:
            if isinstance(plant, str):
                names.append(plant)
                continue
            if not isinstance(plant, dict):
                continue
            for field in ("scientific_name", "common_name"):
                value = plant.get(field)
                if isinstance(value, str) and value.strip():
                    names.append(value.strip())
                    break
    return names


def zones_of(design: dict) -> list[dict]:
    """The zones of a design, as a list of dicts."""
    return [z for z in (design.get("zones") or []) if isinstance(z, dict)]


def plants_of(design: dict) -> list[dict]:
    """Every plant entry of a design, as a list of dicts."""
    out = []
    for zone in zones_of(design):
        for plant in (zone.get("plants") or []):
            if isinstance(plant, dict):
                out.append(plant)
    return out
