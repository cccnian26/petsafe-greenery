"""
Global configuration for the PetSafe-Greenery project.

All tunables live here so that the experiment scripts stay short and the report
can point at exactly one file for "the configuration we used".

Environment variables (optional):
    GEMINI_API_KEY   -- your Google AI Studio key (never commit it to git)
    PETSAFE_MODEL    -- which Gemini model to use (default: gemini-3.5-flash-lite)
    PETSAFE_BACKEND  -- "gemini" (default) or "offline" (no API key needed)

They can be set in the shell, or simply written into a plain-text file called
``.env`` next to ``README.md``::

    GEMINI_API_KEY=your_key_here
    PETSAFE_MODEL=gemini-3.5-flash-lite

``.env`` is already listed in ``.gitignore`` and is excluded from the released
archive, so the key never travels with the submission.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ------------------------------------------------------- console encoding --
# On Windows the console encoding is often cp1252/cp936, and on some systems
# it is plain ASCII.  A model answer can contain a non-ASCII character (an
# em dash, a degree sign, a curly quote, or Chinese text), and printing it
# would then raise UnicodeEncodeError in the middle of the experiment.
# Reconfiguring the two standard streams to UTF-8 with a replacement
# fallback makes that impossible.  It is a no-op on Linux/macOS.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

# --------------------------------------------------------------- .env ------
# A dependency-free reader for a two-line ``.env`` file, so that a beginner
# never has to type ``export`` in a terminal.  Real environment variables
# always win over the file.
def _load_dotenv(path: "Path") -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue
        try:
            os.environ[key] = value
        except UnicodeEncodeError:
            # The environment of this machine cannot hold non-ASCII text
            # (an ASCII locale).  Store an ASCII-safe version instead of
            # crashing the whole run -- and say so, loudly, because a dirty
            # API key is also rejected by the HTTP layer later on.
            cleaned = value.encode("ascii", "replace").decode("ascii")
            bad = [(i, ch) for i, ch in enumerate(value) if ord(ch) > 127]
            where = ", ".join(str(i + 1) for i, _ in bad[:8]) or "?"
            print(f"WARNING: the value of {key} in {path.name} contains "
                  f"{len(bad)} character(s) this system cannot hold in an "
                  f"environment variable (position(s) {where}).")
            print(f"         An ASCII-safe version was used instead.  Please "
                  f"re-copy the value and edit the .env file so it contains "
                  f"nothing but the key itself.")
            os.environ[key] = cleaned


# ------------------------------------------------------- safe JSON writer --
def write_json(path, obj, indent: int = 2) -> None:
    """Write JSON to disk without ever failing on a character encoding.

    A model answer can contain an em dash, a degree sign, a curly quote or
    Chinese text.  On a Windows machine whose locale is ASCII, writing that
    with the default encoding raises UnicodeEncodeError and kills the
    experiment half-way through.  We therefore write UTF-8 explicitly and,
    if even that fails, fall back to pure-ASCII JSON (backslash-u escape
    sequences), which every locale can represent.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent),
                        encoding="utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
        path.write_text(json.dumps(obj, ensure_ascii=True, indent=indent),
                        encoding="ascii")



# ------------------------------------------------------------- API key -----
def sanitize_api_key(raw: str) -> tuple[str, list[str]]:
    """Clean a Gemini API key and report what had to be removed.

    The SDK sends the key in the ``x-goog-api-key`` HTTP header, and every
    HTTP header value is encoded as ASCII (this is the HTTP standard).  If
    the key was copied from a web page and picked up a stray non-ASCII
    character -- a Chinese label, a full-width character, a non-breaking
    space -- the request dies with

        'ascii' codec can't encode characters in position 53-56

    before it ever reaches Google.  We therefore strip anything that cannot
    travel in a header and tell the user exactly what was removed, so the
    key can be re-copied cleanly.

    Returns (clean_key, human readable problem list).
    """
    problems: list[str] = []
    if not raw:
        return "", problems
    original = raw
    key = raw.strip()
    # strip Unicode whitespace that .strip() leaves behind (e.g. NBSP)
    key = key.strip("\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
                    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f"
                    "\u3000\ufeff")
    key = key.strip('"').strip("'")
    if key != original:
        problems.append(
            "leading/trailing whitespace or quotes were removed")
    bad = [(i, ch) for i, ch in enumerate(key) if ord(ch) > 127]
    if bad:
        positions = ", ".join(str(i + 1) for i, _ in bad[:8])
        chars = " ".join(sorted({ch for _, ch in bad}))[:20]
        problems.append(
            f"{len(bad)} character(s) that cannot travel in an HTTP header "
            f"were removed (position(s) {positions}, characters: {chars})")
        key = "".join(ch for ch in key if ord(ch) < 127)
    return key, problems

# ---------------------------------------------------------------- paths ----
ROOT = Path(__file__).resolve().parent.parent
_load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
CACHE_DIR = RESULTS_DIR / "cache"
DATABASE_CSV = Path(os.environ.get("PETSAFE_DB_PATH", DATA_DIR / "plants.csv"))
SCENARIOS_CSV = Path(os.environ.get("PETSAFE_SCENARIOS_PATH", DATA_DIR / "scenarios.csv"))

for _d in (RESULTS_DIR, FIGURES_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------- run directories --
# One directory per (provider, model) pair, so that a second model never
# overwrites the results of the first one, and a re-run with the same model
# only touches its own folder.
RESULTS_RUNS_DIR = RESULTS_DIR / "runs"
LATEST_POINTER = RESULTS_DIR / "latest.json"


def _safe_name(text: str) -> str:
    """A file-system safe version of a model id."""
    out = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text or "")).strip("-")
    return out or "unknown"


def run_dir_name(backend: str, model: str) -> str:
    """Directory name of one run, e.g. 'deepseek__deepseek-v4.1-flash'."""
    return f"{_safe_name(backend)}__{_safe_name(model)}"


def run_dir_for(backend: str, model: str) -> Path:
    """Full path of the result directory belonging to one model."""
    return RESULTS_RUNS_DIR / run_dir_name(backend, model)


def latest_run_dir() -> Path | None:
    """The result directory of the most recent completed run, if any."""
    try:
        info = json.loads(LATEST_POINTER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    name = info.get("run")
    if not name:
        return None
    path = RESULTS_RUNS_DIR / name
    return path if path.is_dir() else None


def list_runs() -> list[dict]:
    """Every finished run, newest first."""
    runs: list[dict] = []
    RESULTS_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(RESULTS_RUNS_DIR.iterdir()):
        if not path.is_dir():
            continue
        manifest = {}
        try:
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}
        runs.append({
            "name": path.name,
            "path": path,
            "backend": manifest.get("backend", ""),
            "model": manifest.get("model", ""),
            "timestamp": manifest.get("timestamp", ""),
            "n_scenarios": manifest.get("n_scenarios", 0),
        })
    runs.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
    # The simulated offline demo is not a run of the experiment, but it is
    # listed (and marked) so that it can never be mistaken for a real one.
    demo = RESULTS_DIR / "offline_demo"
    if demo.is_dir() and (demo / "manifest.json").is_file():
        try:
            manifest = json.loads(
                (demo / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}
        runs.append({
            "name": "offline_demo",
            "path": demo,
            "backend": manifest.get("backend", "offline"),
            "model": manifest.get("model", "offline"),
            "timestamp": manifest.get("timestamp", ""),
            "n_scenarios": manifest.get("n_scenarios", 0),
            "simulated": True,
        })
    return runs

# ---------------------------------------------------------------- model ----
# gemini-3.5-flash-lite : free tier, generous daily quota  -> default
# gemini-3.8-flash     : free tier but a much smaller daily quota, stronger reasoning
# gemini-3.6-flash     : free tier, middle ground
DEFAULT_MODEL = os.environ.get("PETSAFE_MODEL", "gemini-3.5-flash-lite")

# "gemini" uses the real API; "offline" runs the whole pipeline with a
# deterministic local planner so the code can be debugged without a key.
BACKEND = os.environ.get("PETSAFE_BACKEND", "gemini").strip().lower()

API_KEY_ENV = "GEMINI_API_KEY"

# ------------------------------------------------------- DeepSeek / any
# OpenAI-compatible provider -----------------------------------------------
# DeepSeek (and any other service that speaks the OpenAI chat-completions
# protocol) is selected with PETSAFE_BACKEND=deepseek.  The key is read from
# DEEPSEEK_API_KEY, the endpoint from DEEPSEEK_BASE_URL and the model from
# DEEPSEEK_MODEL.
#
# The default model is `deepseek-flash`: it supports tool calls, JSON output
# and streaming, it is the cheapest, and the older names `deepseek-chat` /
# `deepseek-reasoner` have been retired by the provider.
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL",
                                   "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")

# --------------------------------------------------------------- config ----
# How many plants the agent is allowed to put in a single design.
# ------------------------------------------------------------- latency -----
# Two knobs decide how fast a run is.
#
#   PETSAFE_THINKING   off | low | on      (default: off)
#       Gemini 3.x flash models "think" before they answer.  Thinking roughly
#       triples the latency of a long structured answer, and this project does
#       not need it: every checkable property is verified by Python, not by
#       the model's own reasoning.  "low" keeps a small thinking budget if
#       you prefer a slightly better layout.
#
#   PETSAFE_MAX_TOKENS  0 = unlimited      (default: 0)
#       Upper bound on the answer length.  The design schema needs roughly
#       1500-2500 tokens, so 4000 is a safe cap that also stops a runaway
#       generation.
THINKING_MODE = (os.environ.get("PETSAFE_THINKING", "off") or "off").strip().lower()
if THINKING_MODE not in ("off", "low", "on"):
    THINKING_MODE = "off"
try:
    MAX_OUTPUT_TOKENS = int(os.environ.get("PETSAFE_MAX_TOKENS", "0") or 0)
except ValueError:
    MAX_OUTPUT_TOKENS = 0

# ------------------------------------------------- model fallbacks ---------
# The free tier is shared, so a model can be "UNAVAILABLE -- high demand"
# at peak times.  When that happens the run switches to the next model in
# this list.  The choice is made ONCE, before the experiment starts (see
# scripts/run_experiments.py), so all three methods use the same model and
# the comparison stays fair.  The model that was actually used is recorded
# in results/usage.json and in every result file.
# NOTE: the fallback list is EMPTY by default, on purpose.
#
# The free-tier daily limits differ by an order of magnitude:
#     gemini-3.5-flash-lite   ~500 generate_content requests / day
#     gemini-3.6-flash          20 generate_content requests / day
#     gemini-3.8-flash          20 generate_content requests / day
# (the API states the limit in the 429 message; a 20/day model cannot run a
# 25-scenario x 3-method benchmark, which needs about 200 calls.)
#
# So when the primary model is briefly overloaded we WAIT and retry the
# same model instead of switching to one that would run out of quota
# twenty calls later.  Set PETSAFE_MODEL_FALLBACKS explicitly if you want
# to allow a switch.
MODEL_FALLBACKS = [
    m.strip() for m in os.environ.get("PETSAFE_MODEL_FALLBACKS", "").split(",")
    if m.strip()
]

# How long to wait before giving up on a 429 (daily quota exhausted).  The
# free tier resets at midnight Pacific Time, so waiting minutes is pointless:
# fail fast with a message that says what to do.
QUOTA_BACKOFF_SECONDS = int(os.environ.get("PETSAFE_QUOTA_BACKOFF", "8") or 8)

# A 503 ("high demand") is transient, so it gets many more attempts than a
# hard error: 4s, 10s, 22s, 45s, 45s ... up to this many tries.  Any other
# kind of error still fails fast after three tries.
MAX_CAPACITY_ATTEMPTS = int(os.environ.get("PETSAFE_MAX_ATTEMPTS", "10") or 10)
MAX_QUOTA_RETRIES = int(os.environ.get("PETSAFE_MAX_QUOTA_RETRIES", "2") or 2)

DEFAULT_PALETTE_SIZE = 6
# Hard cap on agent tool-call rounds (protects the free-tier daily quota).
MAX_TOOL_ROUNDS = 3

# ---------------------------------------------------------- config tag ----
# Every knob that changes what the pipeline produces is listed here.  The tag
# is written into every result file, and the runner re-runs a scenario whose
# tag does not match.  Without this, results produced by an older version of
# the code would silently be mixed with newer ones -- a methodological
# problem, not just a convenience one.
def _read_version() -> str:
    """The version of this checkout, read from the VERSION file.

    It is printed at the start of every run so that a user can tell at a
    glance which build they are actually running -- the difference between a
    real bug and a stale copy of an old archive is otherwise invisible.
    """
    try:
        v = (Path(__file__).resolve().parent.parent / "VERSION").read_text(
            encoding="utf-8").strip()
        return v or "unknown"
    except OSError:
        return "unknown"


CODE_VERSION = _read_version()
CONFIG_TAG = "|".join([
    f"code={CODE_VERSION}",
    f"palette={DEFAULT_PALETTE_SIZE}",
    f"rounds={MAX_TOOL_ROUNDS}",
    f"think={THINKING_MODE}",
    f"maxtok={MAX_OUTPUT_TOKENS}",
])

# ------------------------------------------------------- viability rules ---
# A plant is horticulturally VIABLE on a site if the site's light class and
# the site's moisture class are both acceptable for that plant.
#
# SEMANTICS of the `light` column of data/plants.csv:
#   it is the SHADIEST LIGHT CONDITION THE PLANT TOLERATES (its shade
#   tolerance limit), not its preferred condition.  NC State Extension lists
#   every condition a plant accepts, so the *least demanding* entry is the
#   tolerance limit and is the value stored.
#
# A plant therefore survives any site that provides at least as much light
# as its tolerance limit requires.  Expressing that as an explicit table
# (rather than as a comparison) keeps the rule auditable and easy to quote
# in the report.
#
# Light levels, from darkest to brightest:
#   full_shade (0) < bright_indirect (1) < partial_shade (2) < full_sun (3)
LIGHT_LEVEL = {
    "full_shade": 0,
    "bright_indirect": 1,
    "partial_shade": 2,
    "full_sun": 3,
}

# site class -> {plant light classes that survive there}
LIGHT_COMPATIBILITY = {
    "full_sun": {"full_sun", "partial_shade", "bright_indirect", "full_shade"},
    "partial_shade": {"partial_shade", "bright_indirect", "full_shade"},
    "bright_indirect": {"bright_indirect", "full_shade"},
    "full_shade": {"full_shade"},
}

# Moisture rule: the site supplies a moisture band and the plant may sit at
# most one step away from it (a wet-soil plant dies on a dry site, a
# dry-soil plant tolerates a moderately moist one, but not the reverse).
MOISTURE_COMPATIBILITY = {
    # site class -> {plant moisture classes that survive there}
    "low": {"low"},
    "moderate": {"low", "moderate"},
    "high": {"moderate", "high"},
}

# Number of plants retrieved by the naive-RAG baseline (it gets no safety filter).
RAG_TOP_K = 8
