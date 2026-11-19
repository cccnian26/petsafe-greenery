# PetSafe-Greenery

**A Dual-Constraint Agentic Workflow for Pet-Friendly Balcony and Courtyard Planting Design**

COMP5511: Artificial Intelligence Concepts — Final Project
Student: CHEN Niannian (26063619G)

---

## 1. What this project does

An LLM asked to design a planting scheme for a balcony shared with a cat will
happily recommend a peace lily, a pothos or a sago palm — species that are
poisonous to the animal living in the room. It will also put sun-loving plants
in a pitch-black north-facing balcony. Both failure modes are *constraint
violations*, and neither is fixed by prompting the model more politely.

This project implements a **multi-tool agentic workflow** that separates the
two kinds of reasoning:

| Stage | Who decides | What it decides |
|-------|-------------|-----------------|
| 1. Constraint extraction | Gemini | reads the brief, extracts light / moisture / pets |
| 2. Candidate retrieval | **deterministic Python** | filters a curated ground-truth database by pet toxicity **and** microclimate |
| 3. Design synthesis | Gemini | composes a spatial design using **only** the verified candidates |
| 4. Audit & self-correction | **deterministic Python** | re-checks every recommended species; triggers one repair round if needed |

The safety-critical decisions are made by code that never hallucinates.
The LLM contributes only what it is good at: language understanding and
spatial design.

## 2. Repository layout

```
petsafe-greenery/
├── README.md                  <- this file
├── requirements.txt
├── app.py                     <- Streamlit demo application
├── data/
│   ├── plants.csv             <- the 150-species curated catalogue
│   ├── plants_extended.csv    <- optional larger catalogue (tiered evidence)
│   ├── aspca_snapshot.json    <- the full ASPCA harvest (tier 2)
│   ├── plantfolio_catalog.json<- the ASPCA-aligned secondary catalogue (tier 3)
│   ├── plant_aliases.json     <- 3872 free-text names -> canonical names
│   ├── source_agreement.json  <- agreement statistics between the sources
│   ├── plants_notes.md        <- how the database was built and verified
│   ├── species_targets.csv    <- the species list that was curated
│   ├── light_overrides.csv    <- manual shade-tolerance values for species
│   │                            that NC State does not list
│   ├── scenarios.csv          <- 25 benchmark scenarios
│   └── raw/                   <- the raw scraped records (provenance)
│       ├── aspca_details.json
│       ├── aspca_full.json
│       ├── plantfolio_common_plants.json
│       └── ncstate_plants.json
├── src/
│   ├── config.py              <- paths, model ids, viability rule tables
│   ├── db.py                  <- database loader + deterministic filter engine
│   ├── tools.py               <- Gemini function declarations + tool implementations
│   ├── llm.py                 <- Gemini wrapper with disk cache, retries, telemetry
│   ├── prompts.py             <- every prompt used in the project
│   ├── schema.py              <- shared JSON output schema + parsing helpers
│   ├── agent.py               <- the proposed dual-constraint workflow
│   ├── baselines.py           <- Baseline 1 (zero-shot) and Baseline 2 (naive RAG)
│   ├── retrieval.py           <- BM25 keyword retrieval for Baseline 2
│   ├── evaluate.py            <- automated evaluation harness
│   ├── rubric.py              <- the Design Completeness rubric (15 binary items)
│   ├── aspca_resolver.py      <- three-tier species resolution with provenance
│   └── offline.py             <- simulator used only for pipeline debugging
├── scripts/
│   ├── fetch_aspca.py         <- data collection: ASPCA toxicity labels
│   ├── fetch_aspca_full.py    <- harvests the WHOLE ASPCA index (1023 plants)
│   ├── fetch_plantfolio.py    <- the ASPCA-aligned secondary catalogue
│   ├── check_sources.py       <- coverage + agreement between the sources
│   ├── build_extended_catalogue.py <- optional larger agent catalogue
│   ├── fetch_ncstate.py       <- data collection: NC State light requirements
│   ├── build_database.py      <- merges everything into data/plants.csv
│   ├── check_database.py      <- validates data/plants.csv
│   ├── smoke_test.py          <- exercises the real agent loop without an API key
│   ├── run_experiments.py     <- runs agent + baselines over all scenarios
│   ├── make_figures.py        <- builds the report/slide figures
│   ├── make_workflow_figure.py<- draws the workflow diagram of the report
│   ├── make_placeholder_figures.py <- neutral placeholders before a real run
│   └── print_rubric.py        <- prints the rubric as markdown / LaTeX
├── docs/
│   ├── START_HERE_CN.md       <- step-by-step guide (Chinese)
│   └── SLIDES_OUTLINE.md      <- slide-by-slide speaker script
├── report/
│   ├── report_skeleton.tex    <- final report skeleton (course format)
│   └── rubric_table.tex       <- rubric table, generated from src/rubric.py
├── results/                   <- raw model outputs + per-scenario metrics
└── figures/                   <- generated charts (PNG + PDF)
```

> **Windows note -- the most common failure on this project.**
> `'ascii' codec can't encode characters in position 53-56` almost always
> means one thing: **the `GEMINI_API_KEY` line in your `.env` contains a
> stray non-ASCII character** (a Chinese label or a full-width character
> copied along with the key). The SDK sends the key in the `x-goog-api-key`
> HTTP header and HTTP headers can only carry ASCII, so the request dies
> before it leaves the machine. Run `python scripts/check_env.py`: it prints
> the exact position of every offending character. Then edit `.env` so that
> the line contains the key and nothing else.
>
> The project is also hardened against the general form of this problem:
> every file is written as UTF-8 explicitly (with an ASCII fallback), the
> console streams are switched to UTF-8 at import time, a non-ASCII API key
> is cleaned and reported, a request whose payload cannot be encoded is
> retried with ASCII-safe content, and the inner traceback of a failed call
> is written to `results/last_error_traceback.txt`. `scripts/smoke_test.py`
> includes regression checks for both the disk cache and the API key.

> **Looking for the step-by-step instructions?** They are in
> [`docs/START_HERE_CN.md`](docs/START_HERE_CN.md) (Chinese, written for a
> beginner) and in Sections 3–5 below.

## 3. Setup

> **Windows / VS Code users:** a step-by-step guide with screenshots-level
> detail lives in `docs/START_HERE_CN.md` (section 3, "方案 B-2"). The short
> version:
>
> ```powershell
> cd petsafe-greenery
> python -m venv .venv
> .venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> ```
>
> Put the API key in a plain file called `.env` in the project root (no
> `export` needed -- `src/config.py` reads it):
>
> ```
> GEMINI_API_KEY=your_key_here
> PETSAFE_MODEL=gemini-3.5-flash-lite
> ```
>
> `.env` is git-ignored and is excluded from the released archive.
>
> Not sure whether your setup is right? Run this first -- it prints every
> problem and the exact command that fixes it:
>
> ```bash
> python scripts/check_env.py
> ```


### Option A — Google Colab (nothing to install locally)

1. Open <https://colab.research.google.com>.
2. Sign in with the same Google account that owns the API key.
3. Upload the project folder (or clone the GitHub repo into the notebook).
4. In a cell, install the dependencies:

```python
!pip install -q google-genai pandas matplotlib
```

5. Set your key (Colab's *Secrets* panel is safer than typing it in a cell):

```python
import os
from google.colab import userdata
os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")
```

### Option B — local Python 3.11+

```bash
cd petsafe-greenery
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"   # Windows: set GEMINI_API_KEY=your-key
# ... or, with DeepSeek:
# export DEEPSEEK_API_KEY="sk-your-key"  +  PETSAFE_BACKEND=deepseek
```

### Choosing a provider

The project runs on **two interchangeable providers**. Everything below the
LLM call -- the tool dispatch, the safety filter, the completeness rubric,
the evaluator -- is identical, so the comparison between the three methods
stays fair no matter which one you pick.

| | **DeepSeek** | **Google AI Studio** |
|---|---|---|
| key variable | `DEEPSEEK_API_KEY` | `GEMINI_API_KEY` |
| selected by | `PETSAFE_BACKEND=deepseek` | `PETSAFE_BACKEND=gemini` |
| endpoint | `https://api.deepseek.com` (OpenAI-compatible) | Google AI Studio |
| model | `deepseek-flash` | `gemini-3.5-flash-lite` |
| daily limit | none (concurrency limit only) | yes, depends on the model |
| cost | paid, but the whole benchmark costs well under 1 USD | free |
| extra dependency | none | none |

The DeepSeek path uses the standard library only (`src/openai_client.py`), so
there is no `openai` package to install and nothing new to break.

**DeepSeek**

1. Sign in at <https://platform.deepseek.com> and **top up the balance** --
   there is no free tier, and an empty balance answers `402`.
2. Create a key at <https://platform.deepseek.com/api_keys> and copy it.
3. Put it in `.env`:

   ```dotenv
   DEEPSEEK_API_KEY=sk-your_key_here
   PETSAFE_BACKEND=deepseek
   PETSAFE_MODEL=deepseek-flash
   ```

> Use `deepseek-flash`. DeepSeek retired the older `deepseek-chat` and
> `deepseek-reasoner` names (2026-07-24). `deepseek-flash` supports tool
> calls, JSON output and streaming.
>
> The client sends `"thinking": {"type": "disabled"}` on every request.
> DeepSeek enables thinking by default, and a request that uses tools while
> thinking is on must echo the `reasoning_content` back, which the API
> rejects with a 400 otherwise.

**Google AI Studio (free)**

1. Go to <https://aistudio.google.com/apikey>.
2. Sign in, accept the terms.
3. Click **Create API key** and copy it. Do **not** commit the key to git.
4. Check your personal quota at <https://aistudio.google.com/rate-limit> —
   the free tier limits depend on the model and can change.

```dotenv
GEMINI_API_KEY=your_key_here
PETSAFE_BACKEND=gemini
PETSAFE_MODEL=gemini-3.5-flash-lite
```

`scripts/check_env.py` is provider-aware: it checks the key that matches your
`PETSAFE_BACKEND`, prints the endpoint and the model, and points at the exact
character position of a malformed key.

### The three "course technique" modules

Three modules implement the lecture techniques explicitly.  They are not
decoration: each one runs in the production pipeline and each one has a test.

| Module | Course topic | What it does | Test |
|---|---|---|---|
| `src/kb.py` | Knowledge representation (L3): Horn clauses, forward chaining | a formal, teachable version of the filter: the safety and microclimate rules as `(premise) => conclusion`, derived by the agenda algorithm with a full firing trace | `scripts/test_kb_parity.py` proves it agrees with the production filter on all 25 scenarios |
| `src/bayes.py` | Uncertainty (L3): Bayes' rule, belief networks | fuses the two toxicity sources in likelihood-ratio form; the parameters are estimated from the measured 90.3% source agreement, not guessed | used by `src/aspca_resolver.py` |
| `src/clustering.py` | Unsupervised learning (L5): k-means | Lloyd iteration from scratch (no scikit-learn) over the *already verified* candidates, so the palette spreads over microclimates without touching the safety filter | used by `src/evaluate.py` (diversity index) |

```
python scripts/test_kb_parity.py      # the formal KB matches the production filter
```

### Filling the slides with the measured numbers

```
python scripts/make_slide_data.py     # results -> slides/data/results.json
cd slides && node compile.js           # rebuild the deck
```

The result table on slide 7 reads its numbers from that JSON, so nothing is
typed by hand, and the slide **refuses simulated (offline) results** -- the
offline demo can never end up in the presentation.

### Running a second model without losing the first run

Every (provider, model) pair gets its own result folder:

```
results/runs/gemini__gemini-3.5-flash-lite/     <- first model
results/runs/deepseek__deepseek-v4.1-flash/      <- second model, untouched
results/latest.json                              <- pointer to the newest run
```

Run the second model exactly as before; the directory is chosen
automatically.  A re-run with the *same* model reuses the cached results
(free) and, when the configuration fingerprint changed, rewrites only that
model's files.  Results written by the old flat layout are moved into the
folder of the model that produced them -- moved, never deleted.

Compare the two sets with

```
python scripts/compare_models.py --all
```

which writes `results/model_comparison.csv`, `.md` and a LaTeX table
(`results/model_comparison.tex`) for the report.  `scripts/make_figures.py`
draws the figures of the most recent run by default; pass `--results` to
pick another one.  `scripts/test_result_isolation.py` is the regression test
for this behaviour (it works in a temporary directory).

### If you move or rename the project folder

A virtual environment is **not relocatable**: the launchers in
`.venv\Scripts\` (`python.exe`, `pip.exe`, `streamlit.exe`) contain the
absolute path of the interpreter as it was at install time, so they keep
pointing at the old folder.  The symptom is

```
Fatal error in launcher: Unable to create process using '"E:\old\...\python.exe"  ...
```

Two ways out:

* immediate: run the module instead of the launcher --
  `.\.venv\Scripts\python.exe -m streamlit run app.py` (and always
  `python -m pip ...`, never the bare `pip`);
* proper: delete `.venv`, run `python -m venv .venv` again and reinstall
  `requirements.txt` in the new location.

Nothing else is affected: `data/`, `results/` and `.env` are all relative
to the project directory and move with it.

### Using another provider (DeepSeek, or any OpenAI-compatible relay)

The project ships with an OpenAI-compatible backend written against the
standard library only -- no new package to install.  To use DeepSeek, or a
relay service, put these four lines in `.env`:

```
PETSAFE_BACKEND=deepseek
DEEPSEEK_BASE_URL=https://sapi.zly163.cn/v1
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
```

The endpoint convention is `POST {base_url}/chat/completions`, so a base URL
that already ends in `/v1` is correct as it stands.  The model name must be
one the provider actually serves (check `GET {base_url}/models`).

Three things happen automatically and are worth knowing:

* the run tag contains the backend and the model, so **all three methods
  always use the same model** -- switching provider therefore cannot
  compromise the fairness of the comparison;
* results produced by the other provider are invalidated and re-run
  (`[stale] ...`), because mixing two models in one results table would be a
  methodological error;
* `scripts/test_deepseek_path.py` exercises the whole DeepSeek path against a
  local mock server, without a key and without spending anything.

Pick the non-reasoning model: the reasoning variant is several times slower
and its chain of thought is worthless here, because every checkable property
of a design is verified by Python rather than by the model.

### Speed and capacity

The free tier is shared, so a model can answer `503 UNAVAILABLE -- high
demand` at peak times, and a model that thinks before answering is slow.
Two knobs and one automatic behaviour handle both:

| knob | default | effect |
|------|---------|--------|
| `PETSAFE_THINKING` | `off` | `off` / `low` / `on`, mapped onto the SDK's `thinking_level` (`MINIMAL` / `LOW` / `HIGH`). Thinking roughly triples the latency of a long structured answer, and this project gains nothing from it: every checkable property is verified in Python. **Note:** Gemini 3.5 and newer reject the older `thinking_budget` parameter with a 400, so the level vocabulary is the only correct one. |
| `PETSAFE_MAX_TOKENS` | `0` (unlimited) | Cap the answer length. 4000 is enough for a full design. |
| `PETSAFE_MODEL_FALLBACKS` | *(empty)* | Models to try when the primary one keeps returning 503. Empty by default on purpose: the free-tier daily limits differ by an order of magnitude (`gemini-3.5-flash-lite` ~500 requests/day, `gemini-3.6-flash` and `gemini-3.8-flash` only ~20), and a benchmark of 25 scenarios x 3 methods needs about 200 calls. When the primary model is briefly overloaded the run waits and retries it instead of switching to a model that would run out of quota twenty calls later. |

`scripts/run_experiments.py` **probes the models before it starts** and picks
one that is answering, so all three methods use the same model and the
comparison stays fair. During the run, every call is timed and printed:

```
      [call] agent_tool        6.2s  in   812 / out  1450 tok
```

Every answer is cached, so a run that is interrupted -- by a 503, by a
quota reset, or by you -- resumes where it stopped without paying twice.

When the daily quota is exhausted the API states the limit and the reset
time in the 429 message; the runner parses both and prints them:

```
The daily free-tier quota is exhausted for model 'gemini-3.6-flash' (20 requests/day).
It resets in 17h 14m.
```

`python scripts/test_gemini_path.py` exercises the whole Gemini path
(real SDK, mocked HTTP layer, no API key needed), which is the fastest way
to check that a change did not break anything before spending quota. It also
replays the two failure modes that actually happened during development: a
model that rejects the thinking configuration (400) and a model that is
overloaded (503).

## 4. Reproducing the main results

```bash
# 0) sanity-check the ground-truth database
python scripts/check_database.py

# 0b) check that the agent loop works without spending API quota
python scripts/smoke_test.py

# 1) run the agent and both baselines over all 25 scenarios
python scripts/run_experiments.py

#    (the run is resumable and every model answer is cached, so re-running
#     costs no API quota; use --force to ignore the cache)

# 2) build the figures
python scripts/make_figures.py

# 3) build the report (from the project root or from report/)
python scripts/print_rubric.py --out report/rubric_table.tex
python scripts/make_workflow_figure.py
cd report && pdflatex report_skeleton.tex && pdflatex report_skeleton.tex
```

The report skeleton compiles as shipped (the figures start as neutral
placeholders and are replaced by the real ones in step 2).

Outputs:

* `results/<method>/<scenario_id>.json` — the full transcript of each design
* `results/metrics_<method>.csv` — per-scenario metrics
* `results/summary.csv` — the aggregate table quoted in the report
* `figures/fig1..fig5` — the charts used in the report and the slides

### Rebuilding the ground-truth database from scratch

The database is produced by scripts, not typed by hand, so it can be rebuilt
and audited:

```bash
python scripts/fetch_aspca.py      # ASPCA  -> data/raw/aspca_details.json
python scripts/fetch_ncstate.py    # NC State -> data/raw/ncstate_plants.json
python scripts/build_database.py   # both   -> data/plants.csv + data/plants_notes.md
```

Raw HTML is cached in `.cache/`, so re-runs do not re-download 250 pages.

### Useful flags

| Flag | Meaning |
|------|---------|
| `--methods agent zeroshot naive_rag` | run only some methods |
| `--start 0 --end 5` | run a slice of the scenarios (useful under a tight daily quota) |
| `--model gemini-3.5-flash-lite` | choose the model (this one has the largest free quota) |
| `--force` | ignore cached results |
| `--backend offline` | run the whole pipeline **without** an API key — simulated data for debugging only, never for the report |

## 5. Running the demo app

```bash
streamlit run app.py
```

Free hosting: push the repository to GitHub and create the app at
<https://share.streamlit.io> (*New app → Connect repository*), then add
`GEMINI_API_KEY` under *Advanced settings → Secrets*.

### Inspecting one scenario side by side

```bash
python scripts/compare_one.py --scenario s02
```

Prints the three designs for a single scenario next to each other, the
metrics table, a *toxicity forensic* (which method picked an unsafe species
and why: from memory / from the retrieved context / filtered out before the
model saw it) and the Design Completeness items each method missed.
It reuses `results/` if the scenario was already run, so it costs nothing.

---

## 6. The ground truth: one authority, two fallbacks, explicit provenance

The curated catalogue (`data/plants.csv`, 150 species) is the agent's
candidate pool. It is deliberately small and every row of it was resolved by
hand against the ASPCA and NC State.

It is **not** a fair yardstick for the baselines. A zero-shot LLM names
species freely; when one of those names falls outside the catalogue the
evaluator cannot certify it, and counting an uncertifiable species as toxic
would flatter the agent -- the agent never proposes anything outside the
catalogue in the first place.

So every recommended name is resolved through a three-tier resolver
(`src/aspca_resolver.py`) that keeps the provenance of each verdict:

| tier | source | authority | role |
|------|--------|-----------|------|
| 1 | `data/plants.csv` | ASPCA + NC State, curated | primary catalogue |
| 2 | `data/aspca_snapshot.json` | ASPCA, full harvest (1 010 of 1 023 listed plants) | authoritative fallback |
| 3 | `data/plantfolio_catalog.json` | `plantfolio-common-plants` (980 records), documented as *ASPCA-aligned* | coverage only |
| -- | `data/plant_aliases.json` | name normalisation | 3 872 free-text names |

Tier 2 is the same veterinary authority as tier 1, harvested in full, so a
species the ASPCA documents is judged just as rigorously whether or not it is
in the curated 150. Tier 3 is used only for species the ASPCA does not list,
and is never treated as authoritative -- the dataset states that it "is not
maintained by horticultural or botanical professionals". The alias map turns
the free-text names models produce ("Peace Lily Sensation", "Zz Plant") into
canonical species names, which is what makes tiers 2 and 3 reachable.

Two safety numbers are therefore reported:

* **`pet_safety_compliance`** -- conservative: a species counts as safe only
  when the ASPCA certifies it. This is the number the safety claim rests on.
* **`pet_safety_compliance_resolved`** -- admits the secondary source and is
  restricted to species that could be judged at all. This is the number that
  compares the methods fairly, because it no longer penalises a baseline for
  naming a species our catalogue happens to omit.

The same treatment applies to horticultural viability
(`horticultural_viability_assessed`, plus a `viability_coverage` figure), and
the gap between the conservative and resolved numbers is reported so no
reader has to guess which is which.

`scripts/check_sources.py` measures the design instead of asserting it:

* the 150 curated species were re-checked against the full harvest -- **0
  verdict mismatches**, so the curated labels are faithful to the ASPCA;
* the two independent sources agree on 140 of their 155 shared species
  (**90.3 %**), and the disagreements are not marginal -- which is why the
  secondary source may extend coverage but never establish safety.

```bash
python scripts/check_sources.py     # coverage, agreement, consistency
```

An optional larger catalogue can be built for the agent (1 363 species: 150
curated + 447 from the full ASPCA harvest + 766 from the ASPCA-aligned
secondary source, 818 of them non-toxic to both cats and dogs):

```bash
python scripts/build_extended_catalogue.py
# then run the experiment with the bigger pool
export PETSAFE_DB_PATH=data/plants_extended.csv
```

---

## 7. The ground-truth database

`data/plants.csv` is the heart of the system. Each row records a species with

| column | meaning |
|--------|---------|
| `id`, `scientific_name`, `common_name` | identity (common names may list synonyms separated by `;`) |
| `plant_type` | planting role (hanging, grass, groundcover, herb, ...) |
| `light` | the **shadiest light condition the plant tolerates**: `full_shade` / `bright_indirect` / `partial_shade` / `full_sun` |
| `moisture` | `low` / `moderate` / `high` |
| `toxic_to_cats`, `toxic_to_dogs` | ground-truth veterinary toxicity labels (0/1) |
| `source_url` | the ASPCA page the label was verified on |
| `notes` | toxicity mechanism and clinical signs, or a care tip |
| `family`, `toxic_principles`, `clinical_signs`, `aspca_toxicity` | the raw ASPCA fields |
| `light_source`, `moisture_source`, `nc_state_tags` | provenance of every horticultural label |

Toxicity labels come from the **ASPCA Animal Poison Control** toxic/non-toxic
plant list; light requirements come from **NC State Extension Plant Toolbox**;
moisture and planting role are curated. Every value is collected by script, so
the database can be rebuilt and audited at any time. See
`data/plants_notes.md` for the per-species provenance, the coverage matrix and
the list of species that were dropped during curation.

### Rebuilding it

```bash
python scripts/fetch_aspca.py      # ASPCA    -> data/raw/aspca_details.json
python scripts/fetch_ncstate.py    # NC State -> data/raw/ncstate_plants.json
python scripts/build_database.py   # both     -> data/plants.csv
```

## 8. Viability rules

A plant counts as *horticulturally viable* on a site when the site provides at
least as much light as the plant tolerates, and the moisture classes are
compatible. The rule tables live in `src/config.py`
(`LIGHT_COMPATIBILITY`, `MOISTURE_COMPATIBILITY`) and are reproduced in the
report. They are deliberately conservative: a sun-loving plant is **not**
viable in deep shade, and a plant that needs wet soil is **not** viable on a
dry site.

If the strict filter finds nothing, the tool relaxes the *horticultural*
constraints along a documented ladder (moisture first, then light) and reports
the relaxation. The **pet-safety filter is never relaxed at any level**.

## 9. What the agent actually produces

A planting scheme is not a list of species, so the output contract obliges the
agent to produce four things beyond the species themselves:

| part | fields | why it matters |
|------|--------|----------------|
| **spatial structure** | `zones[].layer` (`vertical` / `mid` / `ground`), `zone_role`, `placement` incl. the light position | a scheme has to stack in height; exactly one zone must be pet-accessible (`role = grazing`) |
| **combination logic** | `layout_strategy`, `combination_logic`, `plants[].role_in_combination` | how the plants work *together* -- height, texture, colour, scent, seasonal rhythm |
| **care** | `zones[].maintenance`, `care_instructions[{task, frequency, season}]` | what the owner actually has to do, how often, and when |
| **care cautions** | `care_cautions[]` | what goes wrong with *this* scheme: root rot in the hanging baskets, scorch on the hot west wall, frost on the tender perennials, a plant the pet will chew |

All three evaluated methods receive exactly this contract, so the comparison
measures the architecture rather than the prompt.

## 10. The Design Completeness rubric

The completeness metric is **not** a subjective judgement and it is **not** an
LLM-as-judge. It is defined as **15 binary, machine-checkable items** over five
dimensions, each with an explicit detection rule stored in `src/rubric.py`:

| dimension | items | what it checks |
|-----------|-------|----------------|
| Spatial zoning | A1–A3 | a vertical zone, a ground-level zone, a pet-accessible zone |
| Combination logic | B1–B3 | a layering strategy, a combination rationale, a per-plant role |
| Care | C1–C3 | three care instructions, a watering frequency, a light position |
| Care cautions | D1–D3 | two cautions, a concrete named risk, a design-specific caution |
| Pet safety / coverage | E1–E3 | a safety note, that it names the pet, fully populated zones |

An item scores only if the parsed design satisfies its rule; a vague mention
scores nothing. The score is reported in two forms: the full **0–15** and a
compact **0–5** core (A1+A2+A3 = the three spatial zones, C2+C3 = watering
frequency and light position).

```bash
python scripts/print_rubric.py                      # the rubric table (markdown)
python scripts/print_rubric.py --latex              # the same as a LaTeX table
python scripts/print_rubric.py --out report/rubric_table.tex
python scripts/print_rubric.py --check results/agent/s01.json   # score one design
```

The agent also uses the rubric as a **repair signal**: if the design is
missing items, the missing ones are listed back to the model, which gets one
completeness-repair round (the same mechanism as the safety audit).

## 11. Evaluation metrics

All metrics are computed by deterministic Python code against the same
ground-truth database; the evaluator never asks the model whether it was right.

* **Pet safety compliance** — share of recommended plants non-toxic to every household pet
* **Horticultural viability** — share matching the site's light and moisture
* **Dual-constraint accuracy** — share satisfying *both* simultaneously
* **Design completeness** — deterministic rubric over spatial zoning and care advice
* **Out-of-database rate** — share of recommended plants that are not in the database at all
* **Design success rate** — share of scenarios in which a usable design was produced

## 12. Baselines

* **Baseline 1 — direct zero-shot LLM**: one turn, no tools, no database.
* **Baseline 2 — naive keyword RAG**: BM25 retrieval over the same catalogue
  *without* toxicological filtering, then one synthesis turn.
* **Proposed** — the dual-constraint agent above.

## 13. Reproducibility notes

* Every model call is cached under `results/cache/`, so results are stable
  across re-runs and the experiment can be resumed after an interruption.
* The evaluator, the viability rules and the tool implementations are pure
  functions of `data/plants.csv`; nothing depends on wall-clock time.
* `results/usage.json` records the number of model calls, token usage and
  latency per model.

## 14. References

* ASPCA Animal Poison Control — Toxic and Non-Toxic Plants. <https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants>
* NC State Extension Plant Toolbox. <https://plants.ces.ncsu.edu/>
* Missouri Botanical Garden Plant Finder. <https://www.missouribotanicalgarden.org/PlantFinder/>
* Google AI for Developers — Gemini API documentation. <https://ai.google.dev/gemini-api/docs>
* Ning, L. et al. (2025). *A Survey of WebAgents: Towards Next-Generation AI Agents for Web Automation with Large Foundation Models.* arXiv:2503.23350.
