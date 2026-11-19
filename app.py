#!/usr/bin/env python3
"""
Streamlit demo of the PetSafe-Greenery agent.

Run locally:
    streamlit run app.py

Deploy free (Streamlit Community Cloud):
    push this folder to GitHub, then https://share.streamlit.io -> New app
    -> pick the repo, and add GEMINI_API_KEY (or DEEPSEEK_API_KEY) in
       "Advanced settings > Secrets".
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent import run_agent                      # noqa: E402
from src.db import get_database, normalize_light, normalize_moisture, normalize_pets  # noqa: E402
from src.evaluate import evaluate_design            # noqa: E402
from src.llm import LLM                             # noqa: E402
from src.retrieval import BM25Retriever             # noqa: E402
from src.schema import extract_plant_names          # noqa: E402

st.set_page_config(page_title="PetSafe-Greenery", page_icon="🌿", layout="wide")

EXAMPLE_BRIEFS = [
    ("North-facing balcony, partial shade, one cat",
     "My balcony faces north and only gets soft reflected light. I have one "
     "indoor cat who likes to sit among the pots. I want it to look lush."),
    ("Sunny courtyard, full sun, two dogs",
     "Our courtyard gets full sun from midday and is quite dry. Two dogs run "
     "through it and rub against the planters. I want tough, fragrant plants."),
    ("Shaded damp balcony, cat and dog",
     "A small balcony under a dripping pipe so the soil never dries out. "
     "Half shaded. We have a cat and a small dog."),
]

st.title("🌿 PetSafe-Greenery")
st.caption("A dual-constraint agentic workflow for pet-safe balcony and courtyard planting design")

# ------------------------------------------------------------------ setup --
if "db" not in st.session_state:
    st.session_state.db = get_database()
db = st.session_state.db

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox(
        "Provider",
        ["deepseek", "gemini"],
        help="DeepSeek has no daily quota but needs a topped-up balance; "
             "Google AI Studio is free but limits the requests per day.",
    )
    if provider == "deepseek":
        key = st.text_input("DeepSeek API key (or set DEEPSEEK_API_KEY)",
                            value=os.environ.get("DEEPSEEK_API_KEY", ""),
                            type="password")
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key
        model = st.selectbox("Model", ["deepseek-flash"],
                             help="deepseek-chat and deepseek-reasoner have "
                                  "been retired by the provider.")
    else:
        key = st.text_input("Gemini API key (or set GEMINI_API_KEY)",
                            value=os.environ.get("GEMINI_API_KEY", ""),
                            type="password")
        if key:
            os.environ["GEMINI_API_KEY"] = key
        model = st.selectbox(
            "Model",
            ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"],
            help="The Flash-Lite model has the largest free daily quota.",
        )
    st.caption(f"Ground-truth database: **{len(db)} species** "
               f"(ASPCA-sourced toxicity labels)")

st.subheader("1 · Describe your balcony or courtyard")
example = st.selectbox("Or load an example:", ["(write your own)"] + [e[0] for e in EXAMPLE_BRIEFS])
if example != "(write your own)":
    default_brief = dict(EXAMPLE_BRIEFS)[example]
else:
    default_brief = ""

brief = st.text_area("Your brief", value=default_brief, height=120,
                     placeholder="My balcony faces north and only gets soft light. I have one cat...")

run = st.button("Design my planting scheme", type="primary")

if run:
    if not brief.strip():
        st.warning("Please describe your space first.")
    elif provider == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        st.error("No DeepSeek key found. Paste one in the sidebar "
                 "(https://platform.deepseek.com/api_keys).")
    elif provider == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        st.error("No API key found. Paste one in the sidebar (free: "
                 "https://aistudio.google.com/apikey).")
    else:
        with st.spinner("Running the dual-constraint workflow..."):
            llm = LLM(model=model, backend=provider)
            # The agent needs the site parameters; we let the model extract them
            # from the brief itself, exactly as in the experiment.
            scenario = {
                "id": "live",
                "site_type": "balcony",
                "light": "partial_shade",
                "moisture": "moderate",
                "pets": [],
                "brief_detail": brief.strip(),
            }
            # Build the brief exactly like the benchmark does, but keep the
            # user's own wording as the detail line.
            from src.prompts import brief_from_scenario
            scenario["brief_detail"] = brief.strip()
            result = run_agent(llm, scenario)

        st.success("Design ready")

        cols = st.columns([2, 1])
        with cols[0]:
            st.subheader("2 · Planting scheme")
            design = result.get("design", {})
            if design.get("zones"):
                for zone in design["zones"]:
                    with st.expander(f"🌿 {zone.get('zone_name', 'Zone')} "
                                     f"({zone.get('zone_role', '')})", expanded=True):
                        st.caption(zone.get("placement", ""))
                        st.dataframe(
                            [{"Plant": p.get("common_name", ""),
                              "Scientific name": p.get("scientific_name", ""),
                              "Why": p.get("why", "")}
                             for p in zone.get("plants", [])],
                            use_container_width=True, hide_index=True)
            st.subheader("Care instructions")
            for c in design.get("care_instructions", []):
                st.markdown(f"- {c}")
            st.info(design.get("pet_safety_note", ""))

        with cols[1]:
            st.subheader("3 · Safety audit")
            audit = result.get("audit", {})
            if audit.get("audit_passed"):
                st.success("✅ 0 toxic / non-viable plants")
            else:
                st.error(f"⚠️ {audit.get('n_violations', 0)} issue(s) found")
            st.metric("Plants checked", audit.get("n_checked", 0))
            st.metric("Tool calls", result.get("n_tool_calls", 0))
            if result.get("n_repair_rounds"):
                st.metric("Self-correction rounds", result["n_repair_rounds"])
            with st.expander("Agent reasoning trace"):
                st.json(result.get("tool_transcript", []))
            with st.expander("Verified candidate pool"):
                st.json(result.get("candidates", [])[:12])
