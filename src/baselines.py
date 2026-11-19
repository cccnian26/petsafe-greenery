"""
The two baselines that the proposed method is compared against.

Baseline 1 -- Direct Zero-Shot LLM
    One turn, no tools, no database.  The model relies purely on parametric
    memory, which is where the toxic-plant hallucinations come from.

Baseline 2 -- Naive RAG / keyword retrieval
    BM25 keyword retrieval over the same catalogue, with NO toxicological
    filtering, followed by one synthesis turn.  This isolates the effect of
    *grounding* from the effect of *safety filtering*.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .config import RAG_TOP_K
from .llm import LLM
from .prompts import (
    DESIGN_REQUIREMENTS,
    RAG_SYSTEM,
    RAG_USER,
    ZEROSHOT_SYSTEM,
    ZEROSHOT_USER,
    brief_from_scenario,
    format_retrieved,
)
from .retrieval import BM25Retriever
from .schema import DESIGN_SCHEMA, extract_plant_names, parse_json


def run_zeroshot(llm: LLM, scenario: dict) -> dict[str, Any]:
    """Baseline 1: single-turn Gemini, no external knowledge source."""
    t0 = time.time()
    brief = brief_from_scenario(scenario)
    text = llm.generate(
        ZEROSHOT_USER.format(brief=brief, requirements=DESIGN_REQUIREMENTS),
        system_instruction=ZEROSHOT_SYSTEM,
        json_schema=DESIGN_SCHEMA,
        temperature=0.7,
        tag="baseline_zeroshot",
    )
    design = parse_json(text)
    return {
        "method": "baseline1_zeroshot",
        "scenario_id": scenario.get("id"),
        "brief": brief,
        "n_tool_calls": 0,
        "recommended_plants": extract_plant_names(design),
        "design": design,
        "design_text": json.dumps(design, ensure_ascii=False, indent=2),
        "seconds": round(time.time() - t0, 2),
    }


def run_naive_rag(
    llm: LLM, scenario: dict, retriever: BM25Retriever | None = None
) -> dict[str, Any]:
    """Baseline 2: keyword retrieval without negative toxicological filtering."""
    t0 = time.time()
    brief = brief_from_scenario(scenario)
    retriever = retriever or BM25Retriever()
    retrieved = retriever.context(brief, top_k=RAG_TOP_K)
    text = llm.generate(
        RAG_USER.format(brief=brief, retrieved=format_retrieved(retrieved),
                        requirements=DESIGN_REQUIREMENTS),
        system_instruction=RAG_SYSTEM,
        json_schema=DESIGN_SCHEMA,
        temperature=0.7,
        tag="baseline_naive_rag",
    )
    design = parse_json(text)
    return {
        "method": "baseline2_naive_rag",
        "scenario_id": scenario.get("id"),
        "brief": brief,
        "n_tool_calls": 0,
        "retrieved": retrieved,
        "recommended_plants": extract_plant_names(design),
        "design": design,
        "design_text": json.dumps(design, ensure_ascii=False, indent=2),
        "seconds": round(time.time() - t0, 2),
    }


METHODS = {
    "agent": "agent_dual_constraint",
    "zeroshot": "baseline1_zeroshot",
    "naive_rag": "baseline2_naive_rag",
}
