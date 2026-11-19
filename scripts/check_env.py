#!/usr/bin/env python3
"""
One-command environment check.

Run this FIRST, before anything else, if anything looks wrong:

    python scripts/check_env.py

It tells you exactly what is wrong and gives you the exact command to fix it.
It never prints your API key -- only whether one was found.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK = "  OK  "
BAD = " FAIL "
INFO = " INFO "

fixes: list[str] = []
lines: list[str] = []


def say(tag: str, message: str) -> None:
    lines.append(f"[{tag}] {message}")


# ------------------------------------------------------- character encoding --
# The project writes and reads every file as UTF-8 explicitly, so the data is
# safe on any machine.  The console, however, may still be cp1252/cp936/ASCII,
# in which case non-ASCII characters the model returns can look like mojibake
# when printed.  That is cosmetic, but it is worth telling the user once.
try:
    import locale
    pref = locale.getpreferredencoding(False) or ""
except Exception:                                     # pragma: no cover
    pref = ""
console_enc = (getattr(sys.stdout, "encoding", "") or "").lower()
if console_enc in ("ascii", "ansi_x3.4-1968", "us-ascii") or pref.lower() in (
        "ascii", "ansi_x3.4-1968"):
    say(INFO, f"console encoding is '{console_enc or pref}', not UTF-8")
    lines.append(
        "       The project forces UTF-8 for every file it writes, so your "
        "results are safe.")
    lines.append(
        "       If you see mojibake (e.g. '???' or 'â€”') in the console, run "
        "  chcp 65001  once, or set the env var PYTHONUTF8=1 .")
else:
    say(OK, f"console encoding is UTF-8 compatible ({console_enc or pref})")


# ------------------------------------------------------------------ python --
v = sys.version_info
py_ok = v >= (3, 10)
say(OK if py_ok else BAD,
    f"Python {v.major}.{v.minor}.{v.micro} at {sys.executable}")
from src.config import CODE_VERSION  # noqa: E402
say(INFO, f"code version: {CODE_VERSION}")
if not py_ok:
    fixes.append("Install Python 3.11 or newer from https://www.python.org/downloads/ "
                 "(tick 'Add python.exe to PATH'), then restart VS Code.")

in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
if in_venv:
    say(OK, f"virtual environment active: {sys.prefix}")
else:
    say(INFO, "no virtual environment active (fine for this check, "
              "but the experiment needs one)")

# --------------------------------------------------- python version advice --
if v >= (3, 14):
    say(INFO, "Python 3.14 is very new -- some wheels are still missing, "
              "so pip may try to build from source and fail")
    fixes.append("Python 3.12 or 3.13 is the safest for this project.\n"
                 "  py -3.12 -m venv .venv312\n"
                 "  .venv312\\Scripts\\Activate.ps1\n"
                 "  pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/")
elif v < (3, 10):
    pass

# ------------------------------------------------ duplicate environments ----
venvs = sorted(d.name for d in ROOT.iterdir()
               if d.is_dir() and d.name.startswith(".venv"))
if len(venvs) > 1:
    say(INFO, f"several virtual environments exist: {', '.join(venvs)} -- "
              "delete the extras, keep only '.venv'")

# ------------------------------------------------------------------- deps --
missing = []
for mod, pipname in (("google.genai", "google-genai"),
                     ("pandas", "pandas"),
                     ("matplotlib", "matplotlib"),
                     ("streamlit", "streamlit")):
    try:
        __import__(mod)
        say(OK, f"package '{mod}' is installed")
    except Exception:  # noqa: BLE001
        missing.append(pipname)
        say(BAD, f"package '{mod}' is NOT installed")
if missing:
    fixes.append("Install the missing packages:\n"
                 f"    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/\n"
                 f"    (missing: {', '.join(missing)})")

# --------------------------------------------------------------------- key --
try:
    from src import config as _config   # loads .env as a side effect
except Exception as exc:  # noqa: BLE001
    say(INFO, f"could not import src.config ({exc})")
    _config = None

# Which provider is selected?  It decides which key is read, which model is
# used and where the key comes from.
BACKEND = (os.environ.get("PETSAFE_BACKEND", "gemini") or "gemini").lower()
IS_DEEPSEEK = BACKEND.startswith("deepseek")
KEY_NAME = "DEEPSEEK_API_KEY" if IS_DEEPSEEK else "GEMINI_API_KEY"
KEY_URL = ("https://platform.deepseek.com/api_keys" if IS_DEEPSEEK
           else "https://aistudio.google.com/apikey")
DEFAULT_KEY_VALUE = ("sk-your_deepseek_key" if IS_DEEPSEEK else "your_key_here")
DEFAULT_MODEL_NAME = ("deepseek-flash" if IS_DEEPSEEK
                      else "gemini-3.5-flash-lite")
say(INFO, f"backend: {BACKEND}  ->  the key it reads is {KEY_NAME}")

env_file = ROOT / ".env"
key = os.environ.get(KEY_NAME, "")
if key:
    say(OK, f"{KEY_NAME} is set (value hidden)")
elif env_file.exists():
    say(BAD, f"a .env file exists but {KEY_NAME} is empty inside it")
    fixes.append(f"Open the .env file in the project root and paste your key "
                 f"after {KEY_NAME}=  (get one at {KEY_URL})")
else:
    say(BAD, "no API key found (neither the environment nor a .env file)")
    fixes.append(f"Create a file named .env in the project root (same folder as "
                 f"README.md) containing:\n"
                 f"    {KEY_NAME}={DEFAULT_KEY_VALUE}\n"
                 f"    PETSAFE_BACKEND={BACKEND}\n"
                 f"    PETSAFE_MODEL={DEFAULT_MODEL_NAME}")

# ------------------------------------------------------------------- data --
db = ROOT / "data" / "plants.csv"
if db.exists():
    with db.open(encoding="utf-8") as fh:
        n = sum(1 for _ in fh) - 1
    say(OK, f"data/plants.csv present ({n} species)")
else:
    say(BAD, "data/plants.csv is missing -- are you in the right folder?")
    fixes.append("Open the petsafe-greenery folder in VS Code "
                 "(File -> Open Folder...) and run the script from inside it.")

# -------------------------------------------------------- model and quota --
from src.config import (DEFAULT_MODEL, DEEPSEEK_MODEL,  # noqa: E402
                        MODEL_FALLBACKS)

_model = os.environ.get("PETSAFE_MODEL",
                        DEEPSEEK_MODEL if IS_DEEPSEEK else DEFAULT_MODEL)
say(INFO, f"model: {_model}")
say(INFO, f"fallback models: {', '.join(MODEL_FALLBACKS) if MODEL_FALLBACKS else 'none (recommended)'}")
lines.append(
    "       Free-tier daily limits differ hugely: gemini-3.5-flash-lite allows "
    "about 500")
lines.append(
    "       generate_content requests/day, while gemini-3.6-flash and "
    "gemini-3.8-flash allow")
lines.append(
    "       only about 20 -- too few for a 25-scenario x 3-method benchmark "
    "(~200 calls).")

# -------------------------------------------------------------- api key ----
# The key travels in an HTTP header, and HTTP headers are ASCII-only.  A key
# copied from a web page can easily pick up a stray Chinese / full-width
# character, which then kills the request with
#   'ascii' codec can't encode characters in position 53-56
# So check the key explicitly, and say exactly where it is dirty.
from src.config import sanitize_api_key  # noqa: E402

_env_file = ROOT / ".env"
_raw_key = os.environ.get(KEY_NAME, "")
_file_key = ""
if _env_file.exists():
    try:
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line.startswith(f"{KEY_NAME}="):
                _file_key = _line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    except (OSError, UnicodeDecodeError):
        _file_key = ""

for _label, _raw in (("environment", _raw_key), (".env file", _file_key)):
    if not _raw:
        continue
    _clean, _problems = sanitize_api_key(_raw)
    if _problems:
        say(BAD, f"the API key in the {_label} is not clean ASCII")
        for _p in _problems:
            lines.append(f"       -> {_p}")
        _where = KEY_URL
        fixes.append(
            f"Open the .env file in a plain text editor, delete everything on "
            f"the {KEY_NAME} line except the key itself (no Chinese text, no "
            f"full-width characters, no trailing spaces), and copy the key "
            f"again from {_where} .")
        break

# ------------------------------------------------------------------ verdict --
print("=" * 68)
print("PetSafe-Greenery :: environment check")
print("=" * 68)
for line in lines:
    print(line)
print("-" * 68)

if not fixes:
    print("ALL GOOD. Next command:")
    print("    python scripts/smoke_test.py")
else:
    print("WHAT TO DO NEXT:")
    for i, f in enumerate(fixes, 1):
        print(f"  {i}. {f}")
print("=" * 68)

sys.exit(0 if not fixes else 1)
