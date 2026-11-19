"""
The proposed method: a dual-constraint agentic workflow.

Pipeline (exactly the one described in the project proposal, with one
addition that the project proposal already implied -- "the agent must give
care guidelines and layout recommendations"):

  (1) Multi-constraint extraction  -- the model parses the natural-language
      brief and calls the deterministic query tool.
  (2) Deterministic tool execution  -- Python filters the ground-truth
      database by pet toxicity and by microclimate.
  (3) Dual-constraint synthesis    -- the model composes a spatial design
      using ONLY the verified candidates: height layers, combination logic,
      care instructions and care cautions.
  (4a) Self-correction / audit loop -- a deterministic auditor re-checks the
      palette for toxicity and viability; if it fails, the model gets one
      safety repair round.
  (4b) Completeness repair loop      -- a deterministic rubric checks whether
      the design actually contains the spatial structure, combination logic,
      care instructions and care cautions it promises; if items are missing,
      the model gets one completeness repair round.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .config import DEFAULT_PALETTE_SIZE, MAX_TOOL_ROUNDS
from .db import get_database, normalize_light, normalize_moisture, normalize_pets
from .llm import LLM
from .prompts import (
    AGENT_COMPLETENESS_REPAIR_SYSTEM,
    AGENT_REPAIR_SYSTEM,
    AGENT_SYNTHESIS_SYSTEM,
    AGENT_SYSTEM,
    AGENT_USER,
    DESIGN_REQUIREMENTS,
    brief_from_scenario,
    format_candidates,
    format_findings,
    format_missing,
)
from .rubric import score_design
from .schema import DESIGN_SCHEMA, extract_plant_names, parse_json
from .tools import ALL_TOOLS, TOOL_DISPATCH, audit_palette

# A design is "complete enough" when it reaches this share of the rubric.
# 1.0 means "earn all 15 items".  The repair loop still runs at most one
# round and keeps the better of the two designs, so a model that cannot
# reach 15/15 simply reports the score it did reach -- which is exactly the
# honest comparison the report makes (the baselines get no repair round).
COMPLETENESS_TARGET = 1.0


def run_agent(
    llm: LLM,
    scenario: dict,
    max_repair_rounds: int = 1,
    max_completeness_rounds: int = 1,
    completeness_target: float = COMPLETENESS_TARGET,
) -> dict[str, Any]:
    """Run the full dual-constraint workflow on one scenario."""
    t0 = time.time()
    brief = brief_from_scenario(scenario)
    true_pets = normalize_pets(scenario.get("pets", []))
    true_light = normalize_light(scenario.get("light", ""))
    true_moisture = normalize_moisture(scenario.get("moisture", ""))

    # ---------------------------------------------------- stage 1 + 2 ----
    # The model extracts the constraints and calls the deterministic tool.
    turn = llm.tool_loop(
        prompt=AGENT_USER.format(brief=brief, requirements=DESIGN_REQUIREMENTS),
        system_instruction=AGENT_SYSTEM,
        tools=ALL_TOOLS,
        dispatch=TOOL_DISPATCH,
        max_rounds=MAX_TOOL_ROUNDS,
        tag="agent_tool_turn",
    )
    transcript = turn.get("transcript", [])
    tool_call = next(
        (t for t in transcript if t["tool"] == "query_pet_safe_plants"), None
    )
    extracted = tool_call["args"] if tool_call else {}
    candidates = []
    relaxation_note = ""
    if tool_call:
        result = tool_call.get("result", {}) or {}
        candidates = result.get("candidates", []) or []
        relaxation_note = result.get("relaxation_note", "") or ""

    # Fall back to the deterministic query if the model did not call the tool
    # (e.g. the model answered directly).  The pipeline must stay grounded.
    if not candidates:
        from .tools import query_pet_safe_plants

        result = query_pet_safe_plants(
            pets=true_pets, light=true_light, moisture=true_moisture,
            limit=DEFAULT_PALETTE_SIZE,
        )
        candidates = result["candidates"]
        relaxation_note = result.get("relaxation_note", "")
        fallback = True
    else:
        fallback = False

    # ------------------------------------------------- stage 3: synthesis --
    synthesis_prompt = AGENT_SYNTHESIS_SYSTEM.format(
        candidates=format_candidates(candidates, relaxation_note),
        requirements=DESIGN_REQUIREMENTS,
    )
    text = llm.generate(
        synthesis_prompt,
        system_instruction=(
            "You are PetSafe-Greenery. You design pet-safe planting schemes using "
            "only the verified candidate list provided in the prompt."
        ),
        json_schema=DESIGN_SCHEMA,
        temperature=0.4,
        tag="agent_synthesis",
    )
    design = parse_json(text)

    # ------------------------------------------- stage 4a: safety audit ---
    names = extract_plant_names(design)
    findings = audit_palette(names, true_pets, true_light, true_moisture)
    repairs = 0
    repair_history = []

    for _ in range(max_repair_rounds):
        if findings["audit_passed"]:
            break
        repair_prompt = AGENT_REPAIR_SYSTEM.format(
            findings=format_findings(findings),
            candidates=format_candidates(candidates),
        )
        repaired_text = llm.generate(
            repair_prompt,
            system_instruction=(
                "You are PetSafe-Greenery correcting a planting design that failed "
                "the deterministic safety audit."
            ),
            json_schema=DESIGN_SCHEMA,
            temperature=0.2,
            tag="agent_repair",
        )
        repaired = parse_json(repaired_text)
        new_names = extract_plant_names(repaired)
        new_findings = audit_palette(
            new_names, true_pets, true_light, true_moisture
        )
        repairs += 1
        repair_history.append({
            "stage": "safety",
            "before": {"n_violations": findings["n_violations"],
                       "violations": findings["violations"]},
            "after": {"n_violations": new_findings["n_violations"],
                      "violations": new_findings["violations"]},
        })
        # only accept the repair if it does not make things worse
        if new_findings["n_violations"] <= findings["n_violations"]:
            design, findings, names = repaired, new_findings, new_names
        else:
            break

    # ------------------------------- stage 4b: completeness repair loop ---
    completeness = score_design(design)
    completeness_repairs = 0
    completeness_history = []
    for _ in range(max_completeness_rounds):
        if completeness.normalised >= completeness_target:
            break
        if not completeness.missing:
            break
        repair_prompt = AGENT_COMPLETENESS_REPAIR_SYSTEM.format(
            missing=format_missing(completeness.missing),
            candidates=format_candidates(candidates),
        )
        improved_text = llm.generate(
            repair_prompt,
            system_instruction=(
                "You are PetSafe-Greenery completing a planting design that "
                "failed the deterministic design-quality rubric."
            ),
            json_schema=DESIGN_SCHEMA,
            temperature=0.3,
            tag="agent_completeness_repair",
        )
        improved = parse_json(improved_text)
        new_completeness = score_design(improved)
        completeness_repairs += 1
        completeness_history.append({
            "before": {"score": completeness.score_raw,
                       "missing": completeness.missing},
            "after": {"score": new_completeness.score_raw,
                      "missing": new_completeness.missing},
        })
        if new_completeness.score_raw >= completeness.score_raw:
            design = improved
            completeness = new_completeness
            names = extract_plant_names(design)
            # the repaired design must still be safe
            findings = audit_palette(
                names, true_pets, true_light, true_moisture
            )

    design_text = json.dumps(design, ensure_ascii=False, indent=2)
    return {
        "method": "agent_dual_constraint",
        "scenario_id": scenario.get("id"),
        "brief": brief,
        "extracted_constraints": {
            "pets": normalize_pets(extracted.get("pets", [])),
            "light": normalize_light(extracted.get("light", "")),
            "moisture": normalize_moisture(extracted.get("moisture", "")),
            "plant_type": extracted.get("plant_type"),
        },
        "tool_fallback_used": fallback,
        "n_tool_calls": turn.get("n_calls", 0),
        "tool_transcript": transcript,
        "n_candidates": len(candidates),
        "candidates": candidates,
        "recommended_plants": names,
        "design": design,
        "design_text": design_text,
        "audit": findings,
        "n_repair_rounds": repairs,
        "repair_history": repair_history,
        "completeness_score_raw": completeness.score_raw,
        "completeness_score_core5": completeness.score_core5,
        "completeness_missing": completeness.missing,
        "n_completeness_repair_rounds": completeness_repairs,
        "completeness_repair_history": completeness_history,
        "seconds": round(time.time() - t0, 2),
    }
