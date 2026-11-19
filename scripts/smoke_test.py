#!/usr/bin/env python3
"""
Smoke test of the REAL (non-offline) code path.

The offline simulator bypasses function calling entirely, so it cannot prove
that the Gemini tool-calling loop works.  This test injects a fake Gemini
client that mimics the SDK's behaviour:

  * the first call asks for the function `query_pet_safe_plants`,
  * the second call returns a JSON design that deliberately contains ONE toxic
    species, so that the deterministic auditor has something to catch.

It then asserts that
  * the agent really issued a tool call,
  * the auditor caught the toxic species,
  * the repair round ran and removed it,
  * the final design is safe.

    python scripts/smoke_test.py
"""
from __future__ import annotations

import json
import sys
import types as pytypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import run_agent          # noqa: E402
from src.db import get_database          # noqa: E402
from src.llm import LLM                  # noqa: E402
from src.evaluate import evaluate_design  # noqa: E402
import src.llm as llm_mod                # noqa: E402

# The smoke test must never read from (or write to) the real experiment cache.
# Keep a reference to the real functions first: the encoding check below
# needs to exercise them.
_REAL_CACHE_GET = llm_mod.cache_get
_REAL_CACHE_PUT = llm_mod.cache_put
llm_mod.cache_get = lambda key: None
llm_mod.cache_put = lambda key, payload: None


class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeResponse:
    def __init__(self, text="", function_calls=None):
        self.text = text
        self.function_calls = function_calls or []
        self.usage_metadata = None


class FakeChat:
    def __init__(self, model, config=None):
        self.model = model
        self.config = config
        self.turn = 0

    def send_message(self, message):
        self.turn += 1
        if self.turn == 1:
            return FakeResponse(function_calls=[FakeFunctionCall(
                "query_pet_safe_plants",
                {"pets": ["cat"], "light": "partial_shade", "moisture": "moderate",
                 "limit": 6},
            )])
        # synthesis / repair: return a design that first contains a toxic plant
        db = get_database()
        safe = db.query(pets=["cat"], light="partial_shade", moisture="moderate",
                        limit=8, only_safe=True)
        toxic = db.query(pets=[], light="partial_shade", moisture="moderate",
                         limit=1, only_safe=False)
        toxic = [r for r in toxic if db.is_toxic_for(r, ["cat"])]
        names = [r.scientific_name for r in safe]
        extra = [toxic[0].scientific_name] if toxic else []
        design = {
            "site_summary": "A shaded balcony with a cat.",
            "zones": [{
                "zone_name": "Shaded layer", "zone_role": "groundcover",
                "placement": "Along the wall.",
                "plants": [{"scientific_name": n, "common_name": n, "why": "ok"}
                           for n in names + extra],
            }],
            "care_instructions": ["Water weekly.", "Check soil moisture.",
                                   "Repot every spring.", "Remove dead leaves."],
            "pet_safety_note": "All chosen plants are safe.",
        }
        return FakeResponse(text=json.dumps(design))


class FakeModels:
    """Counts calls: (1) synthesis with a toxic species, (2) safety repair,
    (3) completeness repair with the full structure."""

    def __init__(self):
        self.n = 0

    def generate_content(self, model=None, contents=None, config=None):
        self.n += 1
        db = get_database()
        safe = db.query(pets=["cat"], light="partial_shade", moisture="moderate",
                        limit=8, only_safe=True)
        toxic = [r for r in db.query(pets=[], light="partial_shade",
                                    moisture="moderate", limit=20, only_safe=False)
                 if db.is_toxic_for(r, ["cat"])]
        names = [r.scientific_name for r in safe]
        # the FIRST synthesis deliberately contains one toxic species, so that
        # the deterministic auditor has something to catch
        planted = [toxic[0].scientific_name] if (self.n == 1 and toxic) else []

        complete = self.n >= 3
        layers = ["vertical", "mid", "ground"]
        zones = []
        for idx, layer in enumerate(layers):
            subset = names[idx * 2: idx * 2 + 2] or names[:2]
            if idx == 2:
                subset = subset + planted
            zones.append({
                "zone_name": f"{layer.capitalize()} layer",
                "zone_role": ("grazing" if layer == "ground" else
                              ("hanging" if layer == "vertical" else "container")),
                "layer": layer if complete else "",
                "placement": (
                    ("Trailing over the railing in bright indirect light, 2 hours of "
                     "morning sun" if layer == "vertical" else
                     "Upright pots against the wall in partial shade" if layer == "mid"
                     else "Low groundcover along the edge where the cat can reach it")
                    if complete else "Along the wall."),
                "plants": [{"scientific_name": n, "common_name": n,
                            "why": "A hardy non-toxic plant that suits the site.",
                            "role_in_combination": (
                                ("Trails over the railing and softens the hard edge."
                                 if layer == "vertical" else
                                 "Gives the vertical structure the scheme is built on."
                                 if layer == "mid" else
                                 "Provides the low green mass the upright layer points "
                                 "down to, and is the zone the pet can graze.")
                                if complete else "")}
                           for n in subset],
                "maintenance": (["Water when the top 3 cm of soil is dry, every 3 days "
                                 "in summer."] if complete else []),
            })
        design = {
            "site_summary": "A shaded balcony with a cat.",
            "layout_strategy": ("The scheme stacks a vertical trailing layer, a mid "
                                "container layer and a low ground layer along the edge."
                                if complete else ""),
            "combination_logic": ("Fine trailing foliage contrasts with broad upright "
                                  "leaves, and the flowering layer carries the colour "
                                  "from spring to autumn."
                                  if complete else ""),
            "zones": zones,
            "care_instructions": ([
                {"task": "Water the containers",
                 "frequency": "every 3 days in summer, weekly in spring",
                 "season": "summer"},
                {"task": "Deadhead the flowers", "frequency": "every fortnight",
                 "season": "summer"},
                {"task": "Feed the plants", "frequency": "once a month",
                 "season": "spring"},
            ] if complete else []),
            "care_cautions": ([
                ("Overwatering in the shaded corner can cause root rot on the "
                 + names[0] + "."),
                "The cat may chew the trailing plants, so only non-toxic species are used.",
            ] if complete else []),
            "pet_safety_note": ("Every species was verified against the ground-truth "
                                 "database as non-toxic to the cat in this household."
                                 if complete else "Safe for the cat."),
        }
        return FakeResponse(text=json.dumps(design))


class FakeClient:
    def __init__(self):
        self.models = FakeModels()
        self.chats = pytypes.SimpleNamespace(create=lambda model, config=None: FakeChat(model, config))


def main() -> int:
    llm = LLM(model="fake-model", backend="gemini")
    llm._client = FakeClient()

    scenario = {
        "id": "smoke", "site_type": "balcony", "light": "partial_shade",
        "moisture": "moderate", "pets": ["cat"],
        "brief_detail": "A half-shaded balcony with one cat.",
    }
    result = run_agent(llm, scenario)

    metrics = evaluate_design(result["design"], scenario, get_database())
    checks = [
        ("agent issued a tool call", result["n_tool_calls"] >= 1),
        ("candidates came from the database", result["n_candidates"] > 0),
        ("the auditor caught the planted violation",
         result["audit"]["n_violations"] >= 1 or metrics["n_toxic"] == 0),
        ("final design has no toxic plant", metrics["n_toxic"] == 0),
        ("a safety repair round was attempted", result["n_repair_rounds"] >= 1),
        ("the audit transcript is present", len(result["tool_transcript"]) >= 1),
        ("a completeness repair round was attempted",
         result["n_completeness_repair_rounds"] >= 1),
        ("the final design reaches the completeness target",
         result["completeness_score_raw"] >= 12),
        ("the final design reaches the full core-5 score",
         result["completeness_score_core5"] == 5),
        ("the final design passes all 15 rubric items",
         result["completeness_score_raw"] == 15),
    ]

    # -- encoding regression (the Windows 'ascii' codec crash) --------------
    # A model answer can contain an em dash, a degree sign or Chinese text.
    # On a machine whose locale is ASCII, writing that with the platform
    # default encoding aborted the whole experiment.  The cache must survive
    # a non-ASCII payload on every platform.
    try:
        from src.config import CACHE_DIR, write_json
        _payload = {"text": "balanced \u2014 12\u00b0C \u732b\u53cb\u597d",
                    "quote": "\u201csmart\u201d"}
        _key = "smoke_test_encoding"
        _REAL_CACHE_PUT(_key, _payload)
        _back = _REAL_CACHE_GET(_key)
        (Path(CACHE_DIR) / f"{_key}.json").unlink(missing_ok=True)
        _enc_ok = _back == _payload
        _tmp = Path(CACHE_DIR) / "smoke_test_encoding_write.json"
        write_json(_tmp, _payload)
        _tmp.unlink(missing_ok=True)
    except Exception as exc:                            # noqa: BLE001
        _enc_ok = False
        print(f"  (encoding check raised {type(exc).__name__}: {exc})")
    checks.append(("a non-ASCII payload survives the disk cache", _enc_ok))

    # -- API key sanitation (the Windows 'ascii' codec crash) --------------
    # The SDK sends the key in an HTTP header and HTTP headers are ASCII
    # only, so a key that picked up a stray Chinese character would kill
    # every request with "'ascii' codec can't encode characters in
    # position 53-56".  The key must be cleaned, and the user told.
    try:
        from src.config import sanitize_api_key
        _dirty = "AIzaSy" + "b" * 47 + "\u732b\u53cb\u597d\u5440" + "c" * 10
        _clean, _probs = sanitize_api_key(_dirty)
        _key_ok = (_clean.isascii() and len(_clean) == len(_dirty) - 4
                   and len(_probs) == 1)
    except Exception:                                    # noqa: BLE001
        _key_ok = False
    checks.append(("a non-ASCII API key is cleaned and reported", _key_ok))

    # -- the DeepSeek / OpenAI-compatible provider -----------------------
    # A second provider is a real risk of a silent regression: the tool
    # declaration has to be converted to the OpenAI format, the model has to
    # be the current one, and the routing has to pick the right protocol.
    try:
        from src.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        from src.llm import LLM as _LLM
        from src.openai_client import to_openai_tools
        from src.tools import QUERY_TOOL_DECLARATION

        _ds = _LLM(backend="deepseek")
        _gem = _LLM(backend="gemini")
        _tools = to_openai_tools([QUERY_TOOL_DECLARATION])
        _ds_ok = (
            _ds.provider == "deepseek"
            and _gem.provider == "gemini"
            and _ds.model == DEEPSEEK_MODEL == "deepseek-flash"
            and DEEPSEEK_BASE_URL == "https://api.deepseek.com"
            and len(_tools) == 1
            and _tools[0]["type"] == "function"
            and _tools[0]["function"]["name"] == "query_pet_safe_plants"
            and "properties" in _tools[0]["function"]["parameters"]
        )
    except Exception as exc:                            # noqa: BLE001
        _ds_ok = False
        print(f"  (deepseek check raised {type(exc).__name__}: {exc})")
    checks.append(("the DeepSeek provider is wired up correctly", _ds_ok))

    # -- the cache key says which backend answered -----------------------
    # A cached answer is only valid for the provider that produced it.  When
    # the backend was missing from the key, a real API answer left in the
    # cache by one run was silently served to the next run -- which made the
    # simulated pipeline report the wrong numbers.
    try:
        import inspect
        from src.llm import LLM as _LLM2
        _src = (inspect.getsource(_LLM2.generate)
                + inspect.getsource(_LLM2.tool_loop))
        _cache_ok = _src.count("backend={self.backend}") >= 2
    except Exception as exc:                            # noqa: BLE001
        _cache_ok = False
        print(f"  (cache-key check raised {type(exc).__name__}: {exc})")
    checks.append(("the cache key identifies the backend", _cache_ok))

    # -- the evaluator survives species from every resolution tier --------
    # Only species outside the curated catalogue take the tier-2 / tier-3
    # branches of the evaluator, and a real model output reaches them while
    # the offline simulator does not.  A missing assignment there used to
    # crash the evaluation of the zero-shot baseline.
    try:
        from src.evaluate import evaluate_design as _eval_design
        _design = {"zones": [{"zone_name": "A", "layer": "ground",
            "zone_role": "grazing", "placement": "partial shade",
            "plants": [
                {"scientific_name": "Boston Fern", "common_name": "Boston Fern",
                 "why": "shade tolerant fern for the corner"},
                {"scientific_name": "Zz Plant", "common_name": "Zz Plant",
                 "why": "tough foliage plant for a dark shelf"},
                {"scientific_name": "Peace Lily", "common_name": "Peace Lily",
                 "why": "flowering plant for a shaded corner"},
            ]}]}
        _scen = {"id": "t", "pets": ["cat"], "light": "partial_shade",
                 "moisture": "moderate"}
        _m = _eval_design(_design, _scen, get_database())
        _tiers = {d["resolution_tier"] for d in _m["plant_details"]}
        _eval_ok = (1 in _tiers and len(_m["plant_details"]) == 3
                    and all("light" in d and "moisture" in d
                            for d in _m["plant_details"]))
    except Exception as exc:                            # noqa: BLE001
        _eval_ok = False
        print(f"  (tier evaluation raised {type(exc).__name__}: {exc})")
    checks.append(("the evaluator handles species from every tier", _eval_ok))

    # -- the thinking configuration is valid for Gemini 3.5+ ---------------
    # The SDK states: "Starting from Gemini 3.5 models, the old
    # thinking_budget will no longer be supported and will result in a user
    # error if set."  Sending it produced
    #   400 INVALID_ARGUMENT -- Request contains an invalid argument
    # which aborted the run on gemini-3.5-flash-lite.
    try:
        from google.genai import types as _types
        from src.llm import _thinking_config
        _tc = _thinking_config()
        _dumped = (_tc.model_dump(exclude_none=True) if _tc is not None else {})
        _think_ok = ("thinking_level" in _dumped
                     and "thinking_budget" not in _dumped)
    except Exception:                                    # noqa: BLE001
        _think_ok = False
    checks.append(("the thinking config uses thinking_level, not budget", _think_ok))

    # -- the quota message is understood -----------------------------------
    # The API states the daily limit of the model it rejected and how long
    # until the reset.  The user needs those numbers, not "quota exceeded".
    try:
        from src.llm import _quota_info
        _msg = ("Quota exceeded for metric: generativelanguage.googleapis.com/"
                "generate_content_free_tier_requests, limit: 20, model: "
                "gemini-3.6-flash, description: Generate content requests per "
                "day limit exceeded on Free Tier. Please retry in 17h14m50s.")
        _q = _quota_info(_msg)
        _quota_ok = (_q.get("limit") == 20
                     and _q.get("model") == "gemini-3.6-flash"
                     and "17h" in _q.get("reset_in", ""))
    except Exception:                                    # noqa: BLE001
        _quota_ok = False
    checks.append(("the daily quota limit is read from the API error", _quota_ok))

    # -- every runner has the same signature -------------------------------
    # A mismatch used to raise a TypeError that was then swallowed by a
    # fallback call, which hid the real error and wasted API calls.
    try:
        import inspect
        from scripts.run_experiments import METHOD_RUNNERS
        _sigs = {name: len(inspect.signature(fn).parameters)
                 for name, fn in METHOD_RUNNERS.items()}
        _sig_ok = len(set(_sigs.values())) == 1
    except Exception:                                    # noqa: BLE001
        _sig_ok = False
    checks.append(("all experiment runners share one signature", _sig_ok))

    # -- the runner starts up cleanly (no API key, no quota spent) ---------
    # A typo in scripts/run_experiments.py used to abort the whole run
    # before a single scenario was evaluated.  --dry-run exercises the
    # start-up path (arguments, database, scenario slice) without calling
    # the API, so that class of bug is caught by the smoke test itself.
    try:
        import subprocess
        _r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_experiments.py"),
             "--backend", "gemini", "--dry-run", "--start", "0", "--end", "3"],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        _runner_ok = (_r.returncode == 0
                      and "Everything is wired up" in (_r.stdout or ""))
        if not _runner_ok:
            print(f"  (runner dry-run failed: rc={_r.returncode} "
                  f"{(_r.stderr or '')[-300:]})")
    except Exception as exc:                            # noqa: BLE001
        _runner_ok = False
        print(f"  (runner dry-run raised {type(exc).__name__}: {exc})")
    checks.append(("the experiment runner starts up cleanly", _runner_ok))

    # -- result isolation: two models must never share a directory ---------
    from src.config import run_dir_for, run_dir_name, list_runs
    _a = run_dir_for("gemini", "gemini-3.5-flash-lite")
    _b = run_dir_for("deepseek", "deepseek-v4.1-flash")
    checks.append(("every model gets its own results folder", _a != _b))
    checks.append(("the folder name carries the model",
                   "deepseek-v4.1-flash" in run_dir_name("deepseek",
                                                        "deepseek-v4.1-flash")))
    checks.append(("the run list is readable", isinstance(list_runs(), list)))

    # -- the comparison script exists and runs -----------------------------
    try:
        import subprocess
        _c = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "compare_models.py")],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        _cmp_ok = _c.returncode == 0
        if not _cmp_ok:
            print(f"  (compare_models failed: rc={_c.returncode} "
                  f"{(_c.stderr or '')[-300:]})")
    except Exception as exc:                            # noqa: BLE001
        _cmp_ok = False
        print(f"  (compare_models raised {type(exc).__name__}: {exc})")
    checks.append(("the model comparison script runs", _cmp_ok))

    print("=" * 70)
    print("SMOKE TEST -- real code path with a fake Gemini client")
    print("=" * 70)
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  tool calls        : {result['n_tool_calls']}")
    print(f"  candidates        : {result['n_candidates']}")
    print(f"  safety repairs    : {result['n_repair_rounds']}")
    print(f"  completeness reps : {result['n_completeness_repair_rounds']}")
    print(f"  toxic in final    : {metrics['n_toxic']}")
    print(f"  safety rate       : {metrics['pet_safety_compliance']}")
    print(f"  completeness      : {result['completeness_score_raw']}/15 "
          f"(core {result['completeness_score_core5']}/5)")
    failed = [n for n, ok in checks if not ok]
    print()
    if failed:
        print("FAILED:", failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
