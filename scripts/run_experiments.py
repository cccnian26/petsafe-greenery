#!/usr/bin/env python3
"""
Run the whole experiment: proposed agent + two baselines over all scenarios.

    # real run (needs GEMINI_API_KEY)
    python scripts/run_experiments.py

    # only the agent, first 5 scenarios
    python scripts/run_experiments.py --methods agent --end 5

    # pipeline test without an API key (simulated data, written elsewhere)
    python scripts/run_experiments.py --backend offline

Every LLM answer is cached under results/cache/, so re-running is free and
an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import run_agent                                  # noqa: E402
from src.baselines import run_naive_rag, run_zeroshot             # noqa: E402
from src.config import (BACKEND, CODE_VERSION, CONFIG_TAG,  # noqa: E402
                       DATABASE_CSV, DEFAULT_MODEL, LATEST_POINTER,
                       MAX_OUTPUT_TOKENS,
                       MODEL_FALLBACKS, RESULTS_DIR, RESULTS_RUNS_DIR,
                       SCENARIOS_CSV, THINKING_MODE, run_dir_for, write_json)
from src.db import get_database                                  # noqa: E402
from src.evaluate import evaluate_design, summarise              # noqa: E402
from src.llm import LLM, USAGE                                   # noqa: E402
from src.offline import make_offline_handler                     # noqa: E402
from src.retrieval import BM25Retriever                          # noqa: E402

# Every runner takes the same three arguments.  Keeping the signatures
# identical means a method can be swapped or added without touching the
# call site -- and, more importantly, no exception has to be caught to work
# around a mismatched signature (which would also swallow real errors).
METHOD_RUNNERS = {
    "agent": lambda llm, s, r=None: run_agent(llm, s),
    "zeroshot": lambda llm, s, r=None: run_zeroshot(llm, s),
    # the retriever is built once and shared: rebuilding the BM25 index for
    # every scenario is pure waste
    "naive_rag": lambda llm, s, r=None: run_naive_rag(llm, s, retriever=r),
}


def self_check() -> list[str]:
    """Verify that this checkout is internally consistent.

    A stale archive -- or one that was only partly overwritten -- shows up
    here, before a single API call is made and before any quota is spent.
    The three checks below correspond to the three failures that actually
    happened while this project was being built:

    1. the thinking configuration must use ``thinking_level``; Gemini 3.5+
       rejects the older ``thinking_budget`` with a 400;
    2. all three experiment runners must share one signature;
    3. the VERSION file must be readable and match the running code.
    """
    problems: list[str] = []

    try:
        from src.llm import _thinking_config
        _tc = _thinking_config()
        _d = _tc.model_dump(exclude_none=True) if _tc is not None else {}
        if "thinking_budget" in _d:
            problems.append(
                "src/llm.py still sends thinking_budget. Gemini 3.5 and newer "
                "reject it with '400 INVALID_ARGUMENT'. Your copy of the code "
                "is out of date.")
    except Exception as exc:                            # noqa: BLE001
        problems.append(f"src/llm.py could not be imported: {exc}")

    try:
        import inspect
        _sigs = {n: len(inspect.signature(f).parameters)
                 for n, f in METHOD_RUNNERS.items()}
        if len(set(_sigs.values())) != 1:
            problems.append(
                f"the experiment runners have different signatures ({_sigs}); "
                "your copy of the code is only partly updated.")
    except Exception as exc:                            # noqa: BLE001
        problems.append(f"the experiment runners could not be inspected: {exc}")

    try:
        _v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        if _v != CODE_VERSION:
            problems.append(
                f"the VERSION file says '{_v}' but the code says "
                f"'{CODE_VERSION}' -- the archive was only partly extracted.")
    except OSError:
        problems.append(
            "the VERSION file is missing -- this archive is incomplete or "
            "out of date.")

    return problems


def migrate_legacy_results() -> int:
    """Move results of the old flat layout into the folder of their model.

    Earlier versions wrote every result straight into ``results/``.  Now
    every (provider, model) pair has its own directory.  This function moves
    the old files -- it never deletes anything -- so that the results of the
    first model survive when a second model is run.
    """
    moved = 0
    for method_dir in sorted(RESULTS_DIR.iterdir()
                             if RESULTS_DIR.is_dir() else []):
        if not method_dir.is_dir() or method_dir.name in (
                "runs", "cache", "offline_demo"):
            continue
        if not any(method_dir.glob("*.json")):
            continue
        for json_path in sorted(method_dir.glob("*.json")):
            try:
                info = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            model = info.get("model")
            if not model:
                continue
            backend = info.get("backend") or _guess_backend(model)
            target_dir = run_dir_for(backend, model) / method_dir.name
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / json_path.name
            if target.exists():
                # keep the newer of the two
                try:
                    if target.stat().st_mtime >= json_path.stat().st_mtime:
                        continue
                except OSError:
                    continue
            json_path.replace(target)
            moved += 1
            print(f"  [moved] {json_path.name} ({model}) -> "
                  f"{target.parent.parent.name}/{target.parent.name}")
    # The aggregate files (summary.csv, metrics_*.csv, rubric_breakdown.csv)
    # belong to the model named in usage.json; they are moved as well.
    usage_path = RESULTS_DIR / "usage.json"
    if usage_path.is_file():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            usage = {}
        _model = usage.get("model")
        _backend = usage.get("backend") or _guess_backend(_model or "")
        if _model:
            target_run = run_dir_for(_backend, _model)
            target_run.mkdir(parents=True, exist_ok=True)
            for name in ["summary.csv", "rubric_breakdown.csv",
                         "usage.json"] + sorted(
                             p.name for p in RESULTS_DIR.glob("metrics_*.csv")):
                src = RESULTS_DIR / name
                dst = target_run / name
                if src.is_file() and not dst.exists():
                    src.replace(dst)
                    print(f"  [moved] {name} -> {target_run.name}")
    if moved:
        print(f"  [moved] {moved} result file(s) into their model folder. "
              f"Old results are safe.")
    return moved


def _guess_backend(model: str) -> str:
    """The provider of results that do not name one (older files).

    The flat layout was only ever used with Gemini, but a model id is a
    reliable hint anyway: DeepSeek models are served by the DeepSeek
    provider.
    """
    return "deepseek" if str(model).lower().startswith("deepseek") else "gemini"


def parse_args():
    p = argparse.ArgumentParser(description="PetSafe-Greenery experiment runner")
    p.add_argument("--methods", nargs="+", default=list(METHOD_RUNNERS),
                   choices=list(METHOD_RUNNERS), help="which methods to run")
    p.add_argument("--backend", default=BACKEND,
                   choices=["gemini", "deepseek", "offline"],
                   help="gemini = Google AI Studio; deepseek = DeepSeek "
                        "(OpenAI-compatible); offline = simulated pipeline test")
    p.add_argument("--model", default=None, help="model id, e.g. gemini-3.8-flash")
    p.add_argument("--start", type=int, default=0, help="first scenario index (0-based)")
    p.add_argument("--end", type=int, default=None, help="stop before this index")
    p.add_argument("--force", action="store_true", help="ignore cached results")
    p.add_argument("--out", default=None,
                   help="output directory (default: results/runs/<backend>__<model>, "
                        "one folder per model so two models never overwrite "
                        "each other)")
    p.add_argument("--dry-run", action="store_true",
                   help="check the setup and print the plan, but make no API "
                        "calls (costs nothing)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    # The final directory depends on the model that is really used, and that
    # is only known after the pre-flight probe below (a fallback may be
    # picked).  So the directory is settled after the probe; this provisional
    # one is only used for the dry-run banner.
    provisional = Path(args.out) if args.out else run_dir_for(
        args.backend, args.model or DEFAULT_MODEL)
    out_dir = provisional

    db = get_database()
    scenarios = pd.read_csv(SCENARIOS_CSV, dtype=str).fillna("")
    scenarios = scenarios.iloc[args.start:args.end].to_dict("records")
    for s in scenarios:
        s["pets"] = [p for p in str(s.get("pets", "")).split("|") if p]

    # The client is created before the banner so the banner can print the
    # model that will really be used (it may come from the environment,
    # e.g. DEEPSEEK_MODEL, and not from the command line).
    llm = LLM(model=args.model, backend=args.backend)

    print("=" * 78)
    print(f"PetSafe-Greenery experiment runner | backend={args.backend} "
          f"| model={llm.model}")
    print(f"code version: {CODE_VERSION}  (build date "
          f"{CODE_VERSION[:10]}; check it matches the VERSION file)")
    print(f"database: {len(db)} species  |  scenarios: {len(scenarios)}")
    print(f"methods: {', '.join(args.methods)}  |  thinking: {THINKING_MODE}  |  "
          f"max tokens: {MAX_OUTPUT_TOKENS or 'unlimited'}")
    print(f"expected API calls: about {len(scenarios) * len(args.methods) * 3} "
          f"(the agent uses 4-6 per scenario, each baseline 1-2)")

    # Catch a stale or half-updated copy of the project before spending any
    # quota on it.
    _problems = self_check()
    if _problems:
        print("\nERROR: this copy of the project is not consistent:")
        for _p in _problems:
            print(f"  - {_p}")
        print("\n       Download the archive again (its file name contains the "
              "version, e.g. petsafe-greenery-v2026-11-12d.zip) and extract it "
              "over the old folder, or delete the old folder first.")
        return 3

    # The tag also carries the provider and the model, so switching from
    # Gemini to DeepSeek (or to another model) invalidates the previous
    # results instead of silently mixing two models in one table.
    run_tag = f"{CONFIG_TAG}|backend={args.backend}|model={llm.model}"

    if args.dry_run:
        print("=" * 78)
        print("DRY RUN -- no API calls are made, nothing is charged")
        print("=" * 78)
        print(f"  backend      : {args.backend}")
        print(f"  model        : {llm.model}")
        print(f"  fallback list: {', '.join(MODEL_FALLBACKS)}")
        print(f"  thinking     : {THINKING_MODE}")
        print(f"  max tokens   : {MAX_OUTPUT_TOKENS or 'unlimited'}")
        print(f"  methods      : {', '.join(args.methods)}")
        print(f"  scenarios    : {len(scenarios)}  "
              f"({', '.join(s.get('id', '?') for s in scenarios)})")
        print(f"  database     : {len(db)} species")
        print(f"  output dir   : {out_dir}")
        for _s in scenarios:
            print(f"    - {_s.get('id')}: light={_s.get('light')} "
                  f"moisture={_s.get('moisture')} pets={_s.get('pets')}")
        print()
        print("Everything is wired up.  Run without --dry-run to start.")
        return 0

    # -- pre-flight: find a model that is actually answering right now ----
    # The free tier is shared, so a model can be "UNAVAILABLE -- high demand"
    # at peak times.  We pick the model ONCE, before any method runs, so all
    # three methods use the same model and the comparison stays fair.
    if args.backend in ("gemini", "deepseek"):
        _candidates = [args.model or llm.model] + [
            m for m in MODEL_FALLBACKS if m != (args.model or llm.model)]
        print(f"checking which model is available ... ({_candidates[0]})",
              flush=True)
        _chosen = None
        _reason = "capacity"
        for _m in _candidates:
            llm.model = _m
            llm.fallbacks = [x for x in MODEL_FALLBACKS if x != _m]
            _ok, _reason = llm.ping()
            if _ok:
                _chosen = _m
                break
        if _chosen is None:
            if _reason == "quota":
                print("\nERROR: today's free-tier quota is exhausted. There is "
                      "no point starting -- wait for the reset (see "
                      "https://ai.dev/rate-limit) or use a model with a larger "
                      "daily limit:  set PETSAFE_MODEL=gemini-3.5-flash-lite")
                return 2
            if _reason == "balance":
                print("\nERROR: the DeepSeek account has no balance left "
                      "(HTTP 402). Top it up at https://platform.deepseek.com .")
                return 2
            if _reason == "auth":
                _key_name = ("DEEPSEEK_API_KEY" if args.backend == "deepseek"
                             else "GEMINI_API_KEY")
                print(f"\nERROR: the API key was rejected. Check the "
                      f"{_key_name} line in your .env file.")
                return 2
            # A temporary capacity problem: start anyway and let the retry
            # logic wait it out.  Quota-poor models are never used as a
            # fallback, because they would run out of quota after ~20 calls.
            print(f"  -> {_candidates[0]} is temporarily overloaded. Starting "
                  f"anyway: each call retries with a backoff, and every "
                  f"finished call is cached.")
            _chosen = _candidates[0]
        if _chosen != _candidates[0]:
            print(f"  -> {_candidates[0]} is overloaded; using {_chosen} for "
                  f"the WHOLE run (all three methods, so the comparison "
                  f"stays fair).")
        llm.model = _chosen
        llm.models_used = [_chosen]
        llm.fallbacks = [m for m in MODEL_FALLBACKS if m != _chosen]
        print(f"  -> model in use: {_chosen}")
    # The model is settled now, so the output directory is settled too:
    # one folder per (provider, model).  A second model therefore writes to
    # its own folder and cannot overwrite the first model's results, while
    # a re-run with the same model reuses (and, when stale, replaces only)
    # the files inside this folder.
    if args.out:
        out_dir = Path(args.out)
    elif args.backend == "offline":
        out_dir = RESULTS_DIR / "offline_demo"
    else:
        out_dir = run_dir_for(args.backend, llm.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  results for this model go to: {out_dir}")

    # Results of an older layout (everything in results/) are moved into the
    # folder of the model that produced them, so that a second model cannot
    # overwrite them.
    migrate_legacy_results()

    print("=" * 78)
    if args.backend == "offline":
        print("!! OFFLINE MODE: outputs are SIMULATED and are written to "
              f"{out_dir}. They must NOT be used as experimental results.")

    retriever = BM25Retriever(db)
    summary_rows, all_metrics = [], []

    for method in args.methods:
        method_dir = out_dir / method
        method_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n--- method: {method} " + "-" * 60)
        if args.backend == "offline":
            llm.register_offline(make_offline_handler(method))
        metric_rows = []
        for i, scenario in enumerate(scenarios, start=1):
            sid = scenario["id"]
            result_path = method_dir / f"{sid}.json"
            t0 = time.time()
            payload = None
            status = "ran"
            if result_path.exists() and not args.force:
                try:
                    _cached = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    _cached = None
                if _cached is not None and _cached.get("config_tag") == run_tag:
                    payload = _cached
                    status = "cached"
                elif _cached is not None:
                    # The result was produced by a different version of the
                    # pipeline, with different settings, or by a different
                    # model/provider.  Re-running it is the only way to keep
                    # every scenario comparable -- mixing results from two
                    # models in one table would be a methodological error.
                    _old = _cached.get("model") or "an older version"
                    print(f"  [stale] {sid} was produced by {_old} with a "
                          f"different configuration -> re-running it")
            if payload is None:
                if args.backend == "offline":
                    llm.register_offline(make_offline_handler(method, {
                        "light": scenario.get("light"),
                        "moisture": scenario.get("moisture"),
                        "pets": scenario.get("pets"),
                    }))
                payload = METHOD_RUNNERS[method](llm, scenario, retriever)
                payload["elapsed_seconds"] = round(time.time() - t0, 2)
                payload["config_tag"] = run_tag
                payload["model"] = llm.model
                write_json(result_path, payload)
                status = "ran"
            metrics = evaluate_design(payload.get("design", {}), scenario, db)
            metrics["method"] = method
            metrics["mean_seconds"] = payload.get("elapsed_seconds", 0.0)
            metrics["n_tool_calls"] = payload.get("n_tool_calls", 0)
            metrics["n_repair_rounds"] = payload.get("n_repair_rounds", 0)
            metrics["n_completeness_repair_rounds"] = payload.get(
                "n_completeness_repair_rounds", 0)
            metrics["n_candidates"] = payload.get("n_candidates", 0)
            # expand the rubric checks into one column per item, so that the
            # per-item pass rate can be tabulated and plotted
            for item_id, ok in (metrics.get("completeness_checks") or {}).items():
                metrics[f"check_{item_id}"] = int(bool(ok))
            metric_rows.append(metrics)
            resolved = metrics.get("pet_safety_compliance_resolved")
            print(f"  [{status:>6}] {sid}  plants={metrics['n_recommended']:<2} "
                  f"safe={metrics['pet_safety_compliance']:.2f} "
                  f"(res={f'{resolved:.2f}' if resolved is not None else 'n/a'}) "
                  f"viable={metrics['horticultural_viability']:.2f} "
                  f"dual={metrics['dual_constraint_accuracy']:.2f} "
                  f"complete={metrics['design_completeness_raw']:>2}/15 "
                  f"unres={metrics.get('n_unresolvable', 0)} "
                  f"({metrics['mean_seconds']}s)")
        if metric_rows:
            mdf = pd.DataFrame(metric_rows)
            mdf.to_csv(out_dir / f"metrics_{method}.csv", index=False)
            all_metrics.extend(metric_rows)
            s = summarise(mdf, method)
            summary_rows.append(s)
            resolved = s.get("pet_safety_compliance_resolved")
            print(f"  >> {method}: safety={s['pet_safety_compliance']:.3f} "
                  f"(resolved="
                  f"{f'{resolved:.3f}' if resolved is not None else 'n/a'}) "
                  f"viability={s['horticultural_viability']:.3f} "
                  f"dual={s['dual_constraint_accuracy']:.3f} "
                  f"completeness={s['design_completeness']:.3f}")

    if summary_rows:
        sdf = pd.DataFrame(summary_rows)
        sdf.to_csv(out_dir / "summary.csv", index=False)
        print("\n" + "=" * 78)
        print(sdf.to_string(index=False))
        print("=" * 78)
        try:
            from src.evaluate import rubric_breakdown

            rb = rubric_breakdown(pd.DataFrame(all_metrics))
            rb.to_csv(out_dir / "rubric_breakdown.csv", index=False)
            print("\nPer-rubric-item pass rate (fraction of scenarios that earn "
                  "the point):")
            print(rb.to_string(index=False))
        except Exception as exc:  # noqa: BLE001
            print(f"(rubric breakdown unavailable: {exc})")

    print("\nAPI usage:", json.dumps(USAGE.as_dict(), indent=2))
    _usage = USAGE.as_dict()
    _usage["model"] = llm.model
    _usage["backend"] = llm.backend
    _usage["models_used"] = list(llm.models_used)
    _usage["thinking"] = THINKING_MODE
    write_json(out_dir / "usage.json", _usage)
    _u = USAGE.as_dict()
    _calls = _u.get("calls", 0) or 0
    _secs = _u.get("total_seconds", 0.0) or 0.0
    if _calls:
        print(f"\n  {_calls} model calls, {_secs / 60:.1f} min total, "
              f"{_secs / _calls:.1f}s per call average.")
        _n_scen_tot = len(scenarios) * len(args.methods)
        print(f"  {_n_scen_tot} scenario x method cells; "
              f"re-running is free (every answer is cached).")
    # A manifest makes the folder self-describing: which provider, which
    # model, which code version, which scenarios.  It is what lets two runs
    # be compared later without guessing.
    write_json(out_dir / "manifest.json", {
        "backend": llm.backend,
        "provider": llm.provider,
        "model": llm.model,
        "models_used": list(llm.models_used),
        "code_version": CODE_VERSION,
        "config_tag": run_tag,
        "thinking": THINKING_MODE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "database": str(DATABASE_CSV),
        "methods": list(args.methods),
        "n_scenarios": len(scenarios),
        "scenario_ids": [s.get("id") for s in scenarios],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "simulated": args.backend == "offline",
    })
    if args.backend != "offline":
        write_json(LATEST_POINTER, {
            "run": out_dir.name,
            "backend": llm.backend,
            "model": llm.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "path": str(out_dir),
        })
        print(f"\n  this run is now the reference: results/runs/{out_dir.name}")
        print(f"  compare it with another model:  "
              f"python scripts\\compare_models.py")

    if args.backend == "offline":
        _kn = ("DEEPSEEK_API_KEY" if args.backend == "deepseek"
               else "GEMINI_API_KEY")
        print(f"\nReminder: these numbers are SIMULATED. Run with a real "
              f"{_kn} for the results that go in the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
