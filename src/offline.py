"""
Offline "planner" used when there is no Gemini API key.

IMPORTANT: this module exists only to let the student debug the *pipeline*
without spending API quota.  Its outputs are a SIMULATION, not experimental
evidence.  Runs that use it are written to ``results/offline_demo/`` and the
figure script refuses to use them unless ``--allow-offline`` is passed
(in which case every chart is stamped "OFFLINE DEMO - NOT REAL RESULTS").

The simulated zero-shot planner deliberately behaves like a typical
"knowledgeable but ungrounded" LLM: it picks attractive, sun-loving plants
(lilies, pothos, sago palm ...) without checking toxicity, and it sometimes
invents a species that is not in the catalogue.  That is exactly the failure
mode the proposed method is designed to remove.
"""
from __future__ import annotations

import json
import random
import re

from .db import get_database, normalize_light, normalize_moisture, normalize_pets

# Species a fashionable LLM loves to recommend -- many of them are lethal
# to cats or dogs, and some are deliberately NOT in the catalogue so that the
# "out of database" hallucination rate is also exercised.
FASHIONABLE = [
    "Lilium", "Epipremnum aureum", "Spathiphyllum wallisii", "Cycas revoluta",
    "Hedera helix", "Nerium oleander", "Monstera deliciosa", "Ficus lyrata",
    "Yucca elephantipes", "Zamioculcas zamiifolia",
]
INVENTED = ["Lavandula angustifolia", "Osteospermum ecklonii", "Pelargonium graveolens"]


def _brief_to_params(prompt: str) -> dict:
    """Recover the site parameters from the rendered natural-language brief.

    Two input formats have to be understood:
      * the natural-language brief  -- "My balcony is full sun with low moisture"
      * the candidate block         -- "light=full_sun | moisture=low"
    """
    light = "partial_shade"
    moisture = "moderate"
    pets: list[str] = []
    low = prompt.lower()

    m = re.search(r"light=([a-z_]+)", low)
    if m:
        light = m.group(1)
    m = re.search(r"moisture=([a-z]+)", low)
    if m:
        moisture = m.group(1)
    else:
        if "high moisture" in low:
            moisture = "high"
        elif "low moisture" in low:
            moisture = "low"

    if not re.search(r"light=([a-z_]+)", low):
        if "full sun" in low:
            light = "full_sun"
        elif "bright indirect" in low:
            light = "bright_indirect"
        elif "partial shade" in low or "part shade" in low:
            light = "partial_shade"
        elif "full shade" in low or "deep shade" in low:
            light = "full_shade"

    if "cat" in low:
        pets.append("cat")
    if "dog" in low:
        pets.append("dog")
    return {"light": light, "moisture": moisture, "pets": pets}


def _zones_from(records, pet_friendly: bool = True) -> list[dict]:
    """Group candidate records into a plausible 3-zone spatial layout."""
    by_type: dict[str, list] = {}
    for r in records:
        by_type.setdefault(r["plant_type"], []).append(r)
    used: set[str] = set()

    def pick(types: list[str], n: int) -> list[dict]:
        out = []
        for t in types:
            for r in by_type.get(t, []):
                if len(out) >= n:
                    return out
                if r["scientific_name"] in used:
                    continue
                used.add(r["scientific_name"])
                out.append(r)
        for t, rs in by_type.items():
            for r in rs:
                if len(out) >= n:
                    return out
                if r["scientific_name"] in used:
                    continue
                used.add(r["scientific_name"])
                out.append(r)
        return out

    hanging = pick(["hanging"], 2)
    grazing = pick(["grass", "herb"], 2) if pet_friendly else []
    ground = pick(["groundcover", "foliage", "succulent", "perennial", "shrub"], 3)

    def plants_block(items, contribution):
        return [{"scientific_name": r["scientific_name"],
                 "common_name": r["common_name"],
                 "why": f"Fits the zone's light and moisture conditions.",
                 "role_in_combination": contribution}
                for r in items]

    zones = []
    if hanging:
        zones.append({
            "zone_name": "Hanging edge", "zone_role": "hanging", "layer": "vertical",
            "placement": "Suspended along the balcony railing, 4-6 hours of morning sun, "
                         "sheltered from strong afternoon wind.",
            "plants": plants_block(hanging, "Softens the railing line and adds the "
                                            "highest layer to the composition."),
            "maintenance": ["Check the hanging baskets for drying out every second day in summer.",
                            "Trim trailing growth monthly so it does not smother the rail."],
        })
    if grazing:
        zones.append({
            "zone_name": "Pet grazing tray", "zone_role": "grazing", "layer": "ground",
            "placement": "Low tray on the floor beside the door where the pet can reach it, "
                         "in dappled shade with even moisture.",
            "plants": plants_block(grazing, "Gives the pet a safe, fresh, reachable plant to "
                                            "interact with and fills the lowest layer."),
            "maintenance": ["Refresh the tray with fresh grass every two weeks.",
                            "Remove any uneaten material to avoid mould."],
        })
    zones.append({
        "zone_name": "Ground and container layer", "zone_role": "groundcover", "layer": "mid",
        "placement": "Main pots against the wall at knee height, in the brightest part of "
                     "the space, with the edges along the floor.",
        "plants": plants_block(ground, "Provides the mid-height mass and the colour and "
                                       "texture that the trailing layer points to."),
        "maintenance": ["Water the container layer once the top 3 cm of soil is dry.",
                        "Deadhead the flowering plants every fortnight.",
                        "Repot the largest container every second spring."],
    })
    return zones


def _design(records, brief_params: str, pet_friendly: bool = True) -> dict:
    pet_word = "cat" if "cat" in brief_params else ("dog" if "dog" in brief_params else "pet")
    return {
        "site_summary": (
            f"Offline simulated design for a {brief_params} site "
            "(pipeline test only -- not an experimental result)."
        ),
        "layout_strategy": (
            "The scheme stacks three height layers: trailing plants hang from the railing "
            "at eye level, container plants form a mid-height mass against the wall, and a "
            "low ground layer runs along the balcony edge, so the eye moves down through "
            "the planting rather than across it."
        ),
        "combination_logic": (
            "The combination works through contrast: fine, trailing foliage against broad "
            "upright leaves; soft green against the warm wall; and a seasonal rhythm in "
            "which the flowering layer carries the colour in summer while the structural "
            "foliage stays green all year."
        ),
        "zones": _zones_from(records, pet_friendly),
        "care_instructions": [
            {"task": "Water the hanging baskets", "frequency": "twice a week in summer, weekly in spring and autumn",
             "season": "summer"},
            {"task": "Water the ground containers", "frequency": "whenever the top 3 cm of soil is dry, about every 3 days",
             "season": "spring to autumn"},
            {"task": "Deadhead the flowering plants", "frequency": "every fortnight", "season": "summer"},
            {"task": "Feed the container plants", "frequency": "once a month in the growing season",
             "season": "spring and summer"},
            {"task": "Repot the largest container", "frequency": "every second year", "season": "spring"},
        ],
        "care_cautions": [
            "Overwatering is the main risk in the hanging baskets on a windy balcony; check them daily in a heatwave or the roots will rot.",
            "The pet grazing tray must stay within reach but the pots on the floor can be chewed, so only safe species are used there.",
            "Tender plants can scorch on the wall in the afternoon sun, so check them after the first hot week.",
        ],
        "pet_safety_note": (
            f"Every species was checked against the ground-truth database for toxicity to the "
            f"{pet_word}, and only non-toxic species were used."
            if pet_friendly else
            "The scheme was chosen for looks; some common balcony favourites are "
            "dangerous if the pet chews them."
        ),
    }


def make_offline_handler(method: str, ctx: dict | None = None):
    """
    Return a `LLM.generate`-compatible handler for the offline backend.

    `ctx` carries the ground-truth site parameters of the scenario currently
    being simulated.  It is used instead of parsing the prompt, because the
    prompts legitimately contain words like "cat" in plant descriptions and
    free-text parsing would then mis-detect the household pets.
    """
    db = get_database()

    def handler(prompt: str, system_instruction=None, tools=None,
                json_schema=None, tag: str = "default") -> str:
        if ctx:
            params = dict(ctx)
        else:
            params = _brief_to_params(prompt)
        light = normalize_light(params.get("light", "partial_shade"))
        moisture = normalize_moisture(params.get("moisture", "moderate"))
        pets = normalize_pets(params.get("pets", []))

        if method == "agent":
            # The proposed method: strictly the verified candidate pool.
            from .tools import query_pet_safe_plants

            res = query_pet_safe_plants(
                pets=pets, light=light, moisture=moisture, limit=8
            )
            records = res["candidates"]
            return json.dumps(_design(records,
                                      f"{light}/{moisture}/{pets or 'no pets'}"),
                              ensure_ascii=False)

        # Baselines: attractive plants first, safety never checked.
        pool = db.query(pets=[], light=light, moisture=moisture, limit=10,
                        only_safe=False)
        records = [r.public_dict() for r in pool]
        rng = random.Random(hash(tag + light + moisture) & 0xFFFF)
        for name in FASHIONABLE:
            if len(records) >= 6:
                break
            records.append({"scientific_name": name, "common_name": name,
                            "plant_type": "foliage", "light": "full_sun",
                            "moisture": "moderate", "notes": "popular balcony plant"})
        if len(records) > 5 and rng.random() < 0.6:
            records.append({"scientific_name": rng.choice(INVENTED),
                            "common_name": rng.choice(INVENTED),
                            "plant_type": "herb", "light": "full_sun",
                            "moisture": "low", "notes": "fragrant herb"})
        return json.dumps(_design(records[:7],
                                  f"{light}/{moisture}/{pets or 'no pets'}",
                                  pet_friendly=False),
                          ensure_ascii=False)

    return handler
