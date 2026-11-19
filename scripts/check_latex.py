#!/usr/bin/env python3
"""Check whether a LaTeX compiler is reachable, and say how to fix it.

    python scripts\\check_latex.py

It answers three questions at once:

  1. is there a LaTeX distribution at all?
  2. is it on the PATH of *this* terminal / this VS Code window?
  3. if not, where is it installed and what is the exact command to fix it?

The LaTeX Workshop extension is a different thing: it is the editor side and
it is already installed.  A missing ``latexmk`` means the *compiler* side is
missing or not on the PATH.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = ["latexmk", "pdflatex", "xelatex", "lualatex", "tectonic"]

# where the usual Windows installations put the binaries
CANDIDATES = [
    r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64",
    r"%LOCALAPPDATA%\Programs\MiKTeX 2.9\miktex\bin\x64",
    r"%APPDATA%\MiKTeX\miktex\bin\x64",
    r"C:\Program Files\MiKTeX\miktex\bin\x64",
    r"C:\Program Files\MiKTeX 2.9\miktex\bin\x64",
    r"C:\texlive\2026\bin\windows",
    r"C:\texlive\2025\bin\windows",
    r"C:\texlive\2024\bin\windows",
]


def expand(path: str) -> str:
    return os.path.expandvars(path)


def on_path() -> dict[str, str]:
    found = {}
    for tool in TOOLS:
        where = shutil.which(tool)
        if where:
            found[tool] = where
    return found


def in_standard_locations() -> dict[str, list[str]]:
    """Binaries that exist on disk but are not on the PATH."""
    hidden: dict[str, list[str]] = {}
    for tool in TOOLS:
        hits = []
        for candidate in CANDIDATES:
            folder = Path(expand(candidate))
            exe = folder / (tool + (".exe" if platform.system() == "Windows"
                                    else ""))
            if exe.is_file():
                hits.append(str(folder))
        if hits:
            hidden[tool] = sorted(set(hits))
    return hidden


def main() -> int:
    print("=" * 70)
    print("LaTeX compiler check")
    print("=" * 70)
    print(f"platform: {platform.system()} {platform.release()}")
    print()

    found = on_path()
    print("[1] on the PATH right now:")
    if found:
        for tool, where in found.items():
            print(f"    OK   {tool:<10} {where}")
    else:
        print("    NONE of " + ", ".join(TOOLS) + " is on the PATH")
    print()

    hidden = in_standard_locations()
    print("[2] installed but not on the PATH:")
    if hidden:
        for tool, folders in hidden.items():
            for folder in folders:
                print(f"    {tool:<10} {folder}")
    else:
        print("    nothing found in the usual installation folders")
    print()

    if found:
        print("-> A compiler is reachable. The 'latexmk ENOENT' error means the")
        print("   recipe asked for latexmk specifically. Use the pdflatex")
        print("   recipe, or install latexmk, or bypass the extension:")
        print()
        print("   python scripts\\build_report.py")
        return 0

    if hidden:
        print("-> A LaTeX distribution IS installed, but this terminal (and this")
        print("   VS Code window) was started before the installation, so it")
        print("   still has the old PATH. Two steps:")
        print()
        print("   1) close VS Code COMPLETELY and open it again")
        print("   2) then run:  python scripts\\check_latex.py")
        print()
        print("   To fix it right now without restarting, paste this into the")
        print("   terminal (it only changes this window):")
        first = list(hidden.values())[0][0]
        print()
        print(f'       $env:PATH += ";{first}"')
        print(f'       latexmk --version')
        print()
        print("   To fix it permanently for your user account:")
        print()
        print(f'       [Environment]::SetEnvironmentVariable("Path", '
              f'$env:PATH + ";{first}", "User")')
        print()
        print("   (then restart VS Code)")
        return 1

    print("-> No LaTeX distribution found at all. The LaTeX Workshop")
    print("   extension is only the editor side; you still need a compiler.")
    print()
    print("   Easiest (no installation, works in 5 minutes):")
    print("     https://overleaf.com  ->  New Project -> Upload Project")
    print("     (upload the whole petsafe-greenery folder as a zip)")
    print()
    print("   Local install (free):")
    print("     https://miktex.org/download")
    print("     tick 'Install missing packages on the fly'")
    print("     then restart VS Code and run this script again")
    print()
    print("   Or bypass the extension entirely once a compiler exists:")
    print("     python scripts\\build_report.py")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
