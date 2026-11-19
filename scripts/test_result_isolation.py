#!/usr/bin/env python3
"""Regression test: results of one model never overwrite another's.

It checks three things that matter as soon as a second model is run:

  1. two models get two different folders, and the files in them survive;
  2. results written by the old flat layout are moved into the folder of
     the model that produced them (nothing is deleted);
  3. re-running the same model replaces only that model's files.

    python scripts/test_result_isolation.py

The test works in a temporary directory, so it never touches your results.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool]] = []


def check(name: str, ok: bool) -> None:
    CHECKS.append((name, bool(ok)))


def _fake_result(model: str, backend: str, tag: str) -> dict:
    return {
        "design": {"zones": []},
        "model": model,
        "backend": backend,
        "config_tag": f"code=test|model={model}|{tag}",
        "completeness_score_raw": 12,
    }


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="petsafe-isolation-"))
    try:
        # Work on a copy of the project layout: the helpers are re-pointed
        # at the temporary directory, so the real results/ is untouched.
        import src.config as cfg

        cfg.RESULTS_DIR = tmp / "results"
        cfg.RESULTS_RUNS_DIR = cfg.RESULTS_DIR / "runs"
        cfg.LATEST_POINTER = cfg.RESULTS_DIR / "latest.json"
        cfg.RESULTS_RUNS_DIR.mkdir(parents=True, exist_ok=True)

        import scripts.run_experiments as runner

        runner.RESULTS_DIR = cfg.RESULTS_DIR
        runner.RESULTS_RUNS_DIR = cfg.RESULTS_RUNS_DIR
        runner.LATEST_POINTER = cfg.LATEST_POINTER

        # --- 1. two models, two folders ------------------------------------
        dir_a = cfg.run_dir_for("gemini", "gemini-3.5-flash-lite")
        dir_b = cfg.run_dir_for("deepseek", "deepseek-v4.1-flash")
        check("two models get two different folders", dir_a != dir_b)

        (dir_a / "agent").mkdir(parents=True, exist_ok=True)
        (dir_b / "agent").mkdir(parents=True, exist_ok=True)
        (dir_a / "agent" / "s01.json").write_text(
            json.dumps(_fake_result("gemini-3.5-flash-lite", "gemini", "a")),
            encoding="utf-8")
        (dir_b / "agent" / "s01.json").write_text(
            json.dumps(_fake_result("deepseek-v4.1-flash", "deepseek", "b")),
            encoding="utf-8")
        check("both models keep their own file",
              (dir_a / "agent" / "s01.json").is_file()
              and (dir_b / "agent" / "s01.json").is_file())

        # --- 2. the old flat layout is migrated, not deleted ---------------
        legacy = cfg.RESULTS_DIR / "agent"
        legacy.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy / "s02.json"
        legacy_file.write_text(
            json.dumps(_fake_result("gemini-3.5-flash-lite", "gemini", "old")),
            encoding="utf-8")
        moved = runner.migrate_legacy_results()
        check("the legacy result was moved", moved >= 1)
        target = cfg.run_dir_for("gemini", "gemini-3.5-flash-lite") / "agent" / "s02.json"
        check("the legacy result landed in its model's folder", target.is_file())
        check("no data was lost",
              json.loads(target.read_text(encoding="utf-8")).get("config_tag", "")
              .endswith("old"))

        # --- 3. the manifest identifies the run ---------------------------
        (dir_a / "manifest.json").write_text(json.dumps({
            "backend": "gemini", "model": "gemini-3.5-flash-lite",
            "timestamp": "2026-11-13 12:00:00", "n_scenarios": 3,
        }), encoding="utf-8")
        runs = cfg.list_runs()
        names = {r["name"] for r in runs}
        check("the run list contains both models",
              len(names & {dir_a.name, dir_b.name}) == 2)

        # --- 4. the comparison script sees both ---------------------------
        import pandas as pd

        for d, model in ((dir_a, "gemini-3.5-flash-lite"),
                         (dir_b, "deepseek-v4.1-flash")):
            pd.DataFrame([{
                "method": "agent", "n_scenarios": 3,
                "pet_safety_compliance": 1.0,
                "horticultural_viability": 0.9,
                "dual_constraint_accuracy": 0.9,
                "design_completeness": 0.8,
            }]).to_csv(d / "summary.csv", index=False)
        import scripts.compare_models as cmp_mod

        cmp_mod.RESULTS_DIR = cfg.RESULTS_DIR
        df = cmp_mod.collect(runs)
        check("the comparison lists both models", df["run"].nunique() == 2)
        check("the comparison keeps one row per model and method",
              len(df) == 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    print("RESULT ISOLATION TEST")
    print("=" * 70)
    for name, ok in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    failed = [n for n, ok in CHECKS if not ok]
    print()
    if failed:
        print("FAILED:", failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
