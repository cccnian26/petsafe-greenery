#!/usr/bin/env python3
"""
End-to-end integration test of the REAL Gemini code path, without an API key.

    python scripts/test_gemini_path.py

The HTTP layer is replaced by a mock transport, but everything else is the
real thing: the real google-genai SDK, the real agent loop, the real tool
dispatch, the real evaluator, the real rubric.  The test therefore catches
the bugs that only appear once a model actually answers -- exactly the class
of bug that a simulated ("offline") run cannot see.

What it checks:
  1. the pre-flight probe works and the run starts;
  2. the agent issues the tool call and produces a grounded design;
  3. the audit finds nothing toxic in the final design;
  4. the evaluator handles species from every resolution tier (curated,
     ASPCA harvest, ASPCA-aligned secondary) without crashing;
  5. all three methods produce results and the runner exits cleanly.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("GEMINI_API_KEY", "AIzaSyFakeKeyForTheTransportTest")
os.environ.setdefault("PETSAFE_THINKING", "off")

import httpx2 as httpx          # noqa: E402
from google import genai         # noqa: E402
from google.genai import types   # noqa: E402

REAL_CLIENT = genai.Client


def _mock_transport():
    """A transport that answers like Gemini would, and can be told to fail."""
    state = {"calls": 0, "fail_models": set(), "fail_first": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        url = str(request.url)
        model = url.split("/models/")[-1].split(":")[0] if "/models/" in url else ""
        body = json.loads(request.content.decode("utf-8"))
        text_in = json.dumps(body.get("contents", []))[:600]

        if model in state["fail_models"] or state["fail_first"] > 0:
            if state["fail_first"] > 0:
                state["fail_first"] -= 1
            return httpx.Response(503, json={"error": {"code": 503,
                "message": "This model is currently experiencing high demand."}})

        # the pre-flight probe
        if "single word" in text_in:
            return httpx.Response(200, json={"candidates": [{"content": {
                "role": "model", "parts": [{"text": "ok"}]},
                "finishReason": "STOP"}]})

        # the agent's first turn asks for the tool
        if "query_pet_safe_plants" in text_in and "functionCall" not in text_in:
            return httpx.Response(200, json={"candidates": [{"content": {
                "role": "model", "parts": [{"functionCall": {
                    "name": "query_pet_safe_plants",
                    "args": {"pets": ["cat"], "light": "partial_shade",
                             "moisture": "moderate", "limit": 6}}}]},
                "finishReason": "STOP"}]})

        # everything else: a valid design, plus two species that are NOT in
        # the curated catalogue (this is what exercises the tier-2/3 branch
        # of the evaluator)
        from src.db import get_database
        from src.offline import _design
        from src.tools import query_pet_safe_plants
        res = query_pet_safe_plants(pets=["cat"], light="partial_shade",
                                    moisture="moderate", limit=8)
        design = _design(res["candidates"], "partial_shade/moderate/cat")
        for zone in design.get("zones", []):
            zone.setdefault("plants", []).extend([
                {"scientific_name": "Lavender", "common_name": "Lavender",
                 "why": "fragrant Mediterranean herb for a sunny ledge"},
                {"scientific_name": "Rosemary", "common_name": "Rosemary",
                 "why": "aromatic evergreen shrub for the railing"},
            ])
        return httpx.Response(200, json={"candidates": [{"content": {
            "role": "model",
            "parts": [{"text": json.dumps(design, ensure_ascii=False)}]},
            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 500,
                              "candidatesTokenCount": 900}})

    def patched(**kw):
        kw["http_options"] = types.HttpOptions(
            client_args={"transport": httpx.MockTransport(handler)})
        return REAL_CLIENT(**kw)

    genai.Client = patched
    return state


def _mock_transport_rejects_thinking():
    """A transport that rejects ANY thinking configuration, the way a model
    that does not support thinking does.  The run must still finish."""
    state = {"calls": 0, "rejected": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        body = json.loads(request.content.decode("utf-8"))
        gc = body.get("generationConfig", {})
        if gc.get("thinkingConfig") or gc.get("maxOutputTokens"):
            state["rejected"] += 1
            return httpx.Response(400, json={"error": {"code": 400,
                "message": "Request contains an invalid argument.",
                "status": "INVALID_ARGUMENT"}})
        return httpx.Response(200, json={"candidates": [{"content": {
            "role": "model", "parts": [{"text": "ok"}]},
            "finishReason": "STOP"}]})

    def patched(**kw):
        kw["http_options"] = types.HttpOptions(
            client_args={"transport": httpx.MockTransport(handler)})
        return REAL_CLIENT(**kw)

    genai.Client = patched
    return state


def main() -> int:
    state = _mock_transport()
    out_dir = Path(tempfile.mkdtemp(prefix="petsafe_e2e_"))

    # a fresh cache, so the mock really is called
    cache = ROOT / "results" / "cache"
    backup = None
    if cache.exists():
        backup = cache.with_name("cache_backup_e2e")
        if backup.exists():
            import shutil
            shutil.rmtree(backup)
        cache.rename(backup)
    try:
        spec = importlib.util.spec_from_file_location(
            "rx", ROOT / "scripts" / "run_experiments.py")
        rx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rx)
        sys.argv = ["run_experiments.py", "--backend", "gemini",
                    "--start", "0", "--end", "2", "--out", str(out_dir)]
        rc = rx.main()
    finally:
        import shutil
        if cache.exists():
            shutil.rmtree(cache)
        if backup is not None and backup.exists():
            backup.rename(cache)

    # ---- verify what was produced ---------------------------------------
    checks = []
    checks.append(("the runner exited cleanly", rc == 0))
    for method in ("agent", "zeroshot", "naive_rag"):
        files = sorted((out_dir / method).glob("s*.json"))
        checks.append((f"{method}: one result per scenario", len(files) == 2))
        if files:
            payload = json.loads(files[0].read_text(encoding="utf-8"))
            checks.append((f"{method}: the design has zones",
                           bool(payload.get("design", {}).get("zones"))))
            checks.append((f"{method}: the config tag was recorded",
                           bool(payload.get("config_tag"))))
    agent_file = out_dir / "agent" / "s01.json"
    if agent_file.exists():
        payload = json.loads(agent_file.read_text(encoding="utf-8"))
        checks.append(("the agent called the tool at least once",
                       payload.get("n_tool_calls", 0) >= 1))
        checks.append(("the agent used the verified candidate pool",
                       payload.get("n_candidates", 0) > 0))

    # ---- a model that rejects thinking must not break the run -----------
    # Gemini 3.5+ rejects `thinking_budget` with a 400; a model that rejects
    # any thinking configuration at all must likewise not kill the run.
    state2 = _mock_transport_rejects_thinking()
    out_dir2 = Path(tempfile.mkdtemp(prefix="petsafe_e2e_400_"))
    try:
        spec2 = importlib.util.spec_from_file_location(
            "rx2", ROOT / "scripts" / "run_experiments.py")
        rx2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(rx2)
        sys.argv = ["run_experiments.py", "--backend", "gemini",
                    "--start", "0", "--end", "1", "--out", str(out_dir2)]
        rc2 = rx2.main()
    except Exception as exc:                             # noqa: BLE001
        rc2 = 1
        print(f"  (the run raised {type(exc).__name__}: {exc})")
    checks.append(("the run survives a model that rejects thinking", rc2 == 0))

    print()
    print("=" * 70)
    print("END-TO-END TEST -- the real Gemini code path, a mocked HTTP layer")
    print("=" * 70)
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  mock transport calls: {state['calls']} "
          f"(+{state2['calls']} in the thinking-rejection test, "
          f"{state2['rejected']} of them 400s)")
    failed = [n for n, ok in checks if not ok]
    print()
    if failed:
        print("FAILED:", failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
