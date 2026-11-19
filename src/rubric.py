"""
The Design Completeness Score.

The point of this module is that the score is **not** a subjective judgement.
Every item is a binary question that can be decided by inspecting the parsed
JSON design, and the exact detection rule is stored next to the item so that
the rubric table can be printed into the report verbatim.

The score has two forms:

  * ``score_raw``   -- 0-15, the full rubric (five dimensions x three items)
  * ``score_core5`` -- 0-5, the compact core used in the headline table:
                       three spatial zones (0-3) + watering frequency and
                       light position (0-2)

A design earns a point only if it demonstrably contains the information.  No
credit is given for a vague mention: the item must match its detection rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from .schema import plants_of, zones_of

# ------------------------------------------------------------- vocabulary --
LAYER_KEYWORDS = {
    "vertical": ["vertical", "hanging", "trailing", "railing", "upper",
                 "canopy", "overhead", "above eye", "wall-mounted", "hung",
                 "suspended", "elevated", "tier one", "top layer", "tallest",
                 "垂", "悬挂", "高架", "上层", "吊挂"],
    "mid": ["mid", "middle", "mid-level", "shelf", "waist", "knee", "chest",
            "mid layer", "middle layer", "中"],
    "ground": ["ground", "floor", "base", "lower", "edging", "groundcover",
               "ground cover", "floor level", "ground level", "lowest",
               "ground layer", "bottom", "foot of", "地面", "底层", "边缘"],
}

HANGING_ROLES = {"hanging", "trailing", "vertical", "edge", "railing", "overhead"}
GROUND_ROLES = {"groundcover", "ground", "floor", "edging", "base",
                "ground level", "ground-level", "low", "low layer"}
GRAZE_ROLES = {"grazing", "sensory", "pet", "pet-friendly", "pet friendly",
               "forage", "foraging", "edible", "snack", "grazing zone"}

COMBINATION_KEYWORDS = [
    "colour", "color", "contrast", "texture", "season", "height", "rhythm",
    "silhouette", "shape", "foliage", "palette", "harmon", "complement",
    "repeat", "mix", "blend", "together", "companion", "co",
    "搭配", "组合", "层次", "色彩", "季相", "呼应", "协调",
]

LIGHT_KEYWORDS = [
    "full sun", "partial shade", "bright indirect", "deep shade", "morning sun",
    "afternoon sun", "am sun", "pm sun", "east-facing", "west-facing",
    "south-facing", "north-facing", "east facing", "west facing",
    "south facing", "north facing", "sun position", "light position",
    "light exposure", "sun exposure", "hours of sun", "hours of direct sun",
    "光照", "向阳", "半阴", "全阴", "日照",
]

WATER_TASK = ["water", "watering", "irrigat", "mist", "spray", "soak", "moisten",
              "浇", "淋", "喷雾"]
WATER_FREQ = [
    r"daily", r"every day", r"each day", r"twice a week", r"once a week",
    r"weekly", r"biweekly", r"fortnight", r"monthly", r"every \d+[- ]?day",
    r"every \d+[- ]?week", r"\d+\s*times? (?:a|per) week", r"\d+\s*day",
    r"每天", r"每周", r"每\s*\d+\s*天", r"隔天", r"两周",
]

CAUTION_RISK = [
    "overwater", "root rot", "drainage", "waterlog", "scorch", "frost",
    "heat", "cold", "sunburn", "toxic", "poison", "chew", "bite", "nibbl",
    "ingest", "swallow", "wind", "storm", "fungal", "pest", "aphid",
    "积水", "烂根", "晒伤", "冻", "误食", "啃", "中毒", "虫害", "掉叶",
]

PET_WORDS = ["cat", "dog", "kitten", "puppy", "feline", "canine", "猫", "狗"]


def _text(value) -> str:
    return str(value or "").strip()


def _blob(*parts) -> str:
    return " ".join(_text(p) for p in parts).lower()


def _has(pattern_list, text: str) -> bool:
    return any(p in text for p in pattern_list)


def _matches(regexes, text: str) -> bool:
    return any(re.search(rx, text) for rx in regexes)


# ------------------------------------------------------------- the checks --
def _zone_has(design: dict, roles: set[str], keywords: list[str]) -> bool:
    for zone in zones_of(design):
        role = _text(zone.get("zone_role")).lower()
        blob = _blob(zone.get("zone_name"), role, zone.get("placement"))
        if role in roles or _has(keywords, blob):
            return True
    return False


def _layer_is(design: dict, layer: str) -> bool:
    for zone in zones_of(design):
        if _text(zone.get("layer")).lower() == layer:
            return True
    return False


def _vertical_zone(design: dict) -> bool:
    return (_layer_is(design, "vertical")
            or _zone_has(design, HANGING_ROLES, LAYER_KEYWORDS["vertical"]))


def _ground_zone(design: dict) -> bool:
    return (_layer_is(design, "ground")
            or _zone_has(design, GROUND_ROLES, LAYER_KEYWORDS["ground"]))


def _pet_zone(design: dict) -> bool:
    return _zone_has(design, GRAZE_ROLES, [
        "cat grass", "catgrass", "graze", "grazing", "nibble", "chew",
        "forage", "foraging", "snack", "pet", "宠物", "啃", "嗅", "宠物友好",
    ])


def _layout_strategy(design: dict) -> bool:
    text = _text(design.get("layout_strategy"))
    if len(text) < 25:
        return False
    low = text.lower()
    return _has(LAYER_KEYWORDS["vertical"], low) or _has(LAYER_KEYWORDS["ground"], low) \
        or _has(LAYER_KEYWORDS["mid"], low)


def _combination_logic(design: dict) -> bool:
    text = _text(design.get("combination_logic"))
    if len(text) < 25:
        return False
    return _has(COMBINATION_KEYWORDS, text.lower())


def _plant_roles(design: dict) -> bool:
    plants = plants_of(design)
    if not plants:
        return False
    return all(len(_text(p.get("role_in_combination"))) >= 8 for p in plants)


def _care_count(design: dict) -> bool:
    care = design.get("care_instructions") or []
    return len(care) >= 3


def _care_watering(design: dict) -> bool:
    for item in design.get("care_instructions") or []:
        if isinstance(item, str):
            blob = item.lower()
        elif isinstance(item, dict):
            blob = _blob(item.get("task"), item.get("frequency"), item.get("season")).lower()
        else:
            continue
        if _has(WATER_TASK, blob) and _matches(WATER_FREQ, blob):
            return True
    return False


def _light_position(design: dict) -> bool:
    for zone in zones_of(design):
        if _has(LIGHT_KEYWORDS, _blob(zone.get("placement")).lower()):
            return True
    for item in design.get("care_instructions") or []:
        if isinstance(item, str):
            blob = item.lower()
        elif isinstance(item, dict):
            blob = _blob(item.get("task"), item.get("frequency"), item.get("season")).lower()
        else:
            continue
        if _has(LIGHT_KEYWORDS, blob):
            return True
    return False


def _caution_count(design: dict) -> bool:
    cautions = [c for c in (design.get("care_cautions") or []) if _text(c)]
    return len(cautions) >= 2


def _caution_risk(design: dict) -> bool:
    for c in design.get("care_cautions") or []:
        if _has(CAUTION_RISK, _text(c).lower()):
            return True
    return False


def _caution_specific(design: dict) -> bool:
    """At least one caution names a plant of this design or one of its zones."""
    names = []
    for plant in plants_of(design):
        for field in ("scientific_name", "common_name"):
            v = _text(plant.get(field))
            if len(v) >= 4:
                names.append(v.lower())
    for zone in zones_of(design):
        v = _text(zone.get("zone_name"))
        if len(v) >= 4:
            names.append(v.lower())
    if not names:
        return False
    for c in design.get("care_cautions") or []:
        low = _text(c).lower()
        if any(n in low for n in names):
            return True
    return False


def _safety_note(design: dict) -> bool:
    return len(_text(design.get("pet_safety_note"))) >= 30


def _safety_note_names_pet(design: dict) -> bool:
    return _has(PET_WORDS, _text(design.get("pet_safety_note")).lower())


def _fully_populated(design: dict) -> bool:
    zones = zones_of(design)
    if not zones:
        return False
    if any(len(z.get("plants") or []) < 2 for z in zones):
        return False
    plants = plants_of(design)
    if not plants:
        return False
    return all(len(_text(p.get("why"))) >= 10 for p in plants)


# ------------------------------------------------------------- the rubric --
@dataclass
class RubricItem:
    id: str
    dimension: str
    item: str
    rule: str
    check: Callable[[dict], bool]
    points: int = 1
    core: bool = False   # part of the compact 0-5 core score


RUBRIC_ITEMS: list[RubricItem] = [
    RubricItem("A1", "Spatial zoning", "Vertical / trailing zone",
               "A zone whose layer is 'vertical', or whose role/name/placement "
               "matches hanging|trailing|railing|upper|canopy|overhead",
               _vertical_zone, core=True),
    RubricItem("A2", "Spatial zoning", "Ground-level zone",
               "A zone whose layer is 'ground', or whose role/name/placement "
               "matches ground|floor|base|lower|edging|groundcover",
               _ground_zone, core=True),
    RubricItem("A3", "Spatial zoning", "Pet-accessible zone",
               "A zone whose role is grazing|sensory|pet|forage|edible, or whose "
               "text mentions cat grass|graze|nibble|chew|forage|pet",
               _pet_zone, core=True),
    RubricItem("B1", "Combination logic", "Spatial layering strategy stated",
               "layout_strategy is >= 25 characters AND names at least one "
               "height layer (vertical|mid|ground)",
               _layout_strategy),
    RubricItem("B2", "Combination logic", "Combination rationale stated",
               "combination_logic is >= 25 characters AND mentions contrast, "
               "texture, colour, height, season or rhythm",
               _combination_logic),
    RubricItem("B3", "Combination logic", "Per-plant role in the composition",
               "every plant has a role_in_combination of >= 8 characters",
               _plant_roles),
    RubricItem("C1", "Care", "At least three care instructions",
               "len(care_instructions) >= 3",
               _care_count),
    RubricItem("C2", "Care", "Watering frequency specified",
               "a care instruction mentions watering AND a frequency "
               "(daily|weekly|every N days|twice a week|monthly)",
               _care_watering, core=True),
    RubricItem("C3", "Care", "Light position specified",
               "a zone placement or a care instruction mentions full sun|partial "
               "shade|bright indirect|deep shade|morning sun|east-facing|...",
               _light_position, core=True),
    RubricItem("D1", "Care cautions", "At least two cautions",
               "len(care_cautions) >= 2",
               _caution_count),
    RubricItem("D2", "Care cautions", "A concrete risk is named",
               "a caution mentions overwatering|root rot|drainage|scorch|frost|"
               "heat|toxic|chew|bite|wind|pest",
               _caution_risk),
    RubricItem("D3", "Care cautions", "The caution is specific to this design",
               "a caution names one of this design's plants or one of its zones",
               _caution_specific),
    RubricItem("E1", "Pet safety", "Safety note present",
               "pet_safety_note is >= 30 characters",
               _safety_note),
    RubricItem("E2", "Pet safety", "Safety note names the pet",
               "pet_safety_note mentions cat|dog",
               _safety_note_names_pet),
    RubricItem("E3", "Coverage", "All zones populated, all plants justified",
               "every zone has >= 2 plants AND every plant has a why of >= 10 "
               "characters",
               _fully_populated),
]

MAX_RAW = sum(i.points for i in RUBRIC_ITEMS)          # 15
MAX_CORE = sum(i.points for i in RUBRIC_ITEMS if i.core)  # 5

DIMENSIONS = ["Spatial zoning", "Combination logic", "Care",
              "Care cautions", "Pet safety", "Coverage"]


@dataclass
class Completeness:
    score_raw: int = 0
    score_core5: int = 0
    max_raw: int = MAX_RAW
    max_core5: int = MAX_CORE
    checks: dict = field(default_factory=dict)
    dimension_scores: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)

    @property
    def normalised(self) -> float:
        return round(self.score_raw / self.max_raw, 4) if self.max_raw else 0.0

    @property
    def normalised_core(self) -> float:
        return round(self.score_core5 / self.max_core5, 4) if self.max_core5 else 0.0

    def as_dict(self) -> dict:
        return {
            "design_completeness_raw": self.score_raw,
            "design_completeness_max_raw": self.max_raw,
            "design_completeness_core5": self.score_core5,
            "design_completeness_max_core5": self.max_core5,
            "design_completeness": self.normalised,
            "design_completeness_core": self.normalised_core,
            "completeness_dimension_scores": self.dimension_scores,
            "completeness_missing": self.missing,
        }


def score_design(design: dict) -> Completeness:
    """Score one design against the full rubric."""
    result = Completeness()
    for item in RUBRIC_ITEMS:
        try:
            ok = bool(item.check(design))
        except Exception:  # noqa: BLE001 - a broken design must not crash the run
            ok = False
        result.checks[item.id] = ok
        if ok:
            result.score_raw += item.points
            if item.core:
                result.score_core5 += item.points
        else:
            result.missing.append(f"{item.id}: {item.item}")

    for dim in DIMENSIONS:
        items = [i for i in RUBRIC_ITEMS if i.dimension == dim]
        result.dimension_scores[dim] = {
            "earned": sum(1 for i in items if result.checks[i.id]),
            "max": len(items),
        }
    return result


def rubric_table_markdown() -> str:
    """The rubric as a markdown table (for the report / README)."""
    lines = ["| ID | Dimension | Item | Detection rule | Pts |",
             "|----|-----------|------|----------------|-----|"]
    for item in RUBRIC_ITEMS:
        rule = " ".join(item.rule.split())
        lines.append(f"| {item.id} | {item.dimension} | {item.item} | {rule} | {item.points} |")
    lines.append(f"\nTotal: **{MAX_RAW}** points "
                 f"(compact core: **{MAX_CORE}** = A1+A2+A3+C2+C3).")
    return "\n".join(lines)


def rubric_table_latex() -> str:
    """The rubric as a LaTeX table (paste straight into the report)."""
    lines = [
        "\\begin{table}[!ht]",
        "\\centering",
        "\\footnotesize",
        "\\begin{tabular}{llp{10.4cm}c}",
        "\\toprule",
        "ID & Dimension & Item and machine-checkable detection rule & Pts \\\\",
        "\\midrule",
    ]
    for item in RUBRIC_ITEMS:
        text = f"{item.item} --- {' '.join(item.rule.split())}"
        text = text.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
        text = text.replace("|", "\\textbar{}")
        dim = item.dimension.replace("&", "\\&")
        lines.append(f"{item.id} & {dim} & {text} & {item.points} \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        f"\\caption{{Design Completeness Score: {len(RUBRIC_ITEMS)} binary, "
        f"machine-checkable items (maximum {MAX_RAW} points). The compact core "
        f"score uses items A1--A3, C2 and C3 (maximum {MAX_CORE} points).}}",
        "\\end{table}",
    ]
    return "\n".join(lines)
