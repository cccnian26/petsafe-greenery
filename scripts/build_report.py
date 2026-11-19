#!/usr/bin/env python3
"""Compile the report with one command.

    python scripts\\build_report.py

It finds pdflatex (or latexmk), compiles twice -- the second pass resolves
the cross-references and the bibliography -- then reports the page count
and the number of LaTeX errors.

No LaTeX extension for VS Code is needed, and no latexmk.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "report"
TEX = "report_skeleton.tex"

NO_LATEX = """
没有找到 LaTeX 编译器（pdflatex / latexmk）。

最快的路（不用装任何东西，5 分钟）：
  1. 打开 https://overleaf.com 注册（免费）
  2. New Project -> Upload Project -> 把整个 petsafe-greenery 文件夹压成 zip 传上去
  3. Main document 选 report/report_skeleton.tex
  4. 点 Recompile，右上角预览，右下角下载 PDF

要本机编译：装 MiKTeX（免费）https://miktex.org/download
  安装时勾选 "Install missing packages on the fly"，装完重开终端再跑一次本脚本。
"""


def find_compiler() -> tuple[str | None, str | None]:
    """(executable, kind) where kind is 'latexmk' or 'pdflatex'."""
    latexmk = shutil.which("latexmk")
    if latexmk:
        return latexmk, "latexmk"
    for name in ("pdflatex", "xelatex", "lualatex"):
        found = shutil.which(name)
        if found:
            return found, name
    return None, None


def compile_once(exe: str, kind: str) -> int:
    if kind == "latexmk":
        cmd = [exe, "-pdf", "-interaction=nonstopmode", "-halt-on-error",
               TEX]
    else:
        cmd = [exe, "-interaction=nonstopmode", TEX]
    print(f"  > {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(REPORT_DIR), capture_output=True,
                          text=True, errors="replace")
    return proc.returncode


def page_count(pdf: Path, log: Path) -> int | None:
    """The page count, without needing a PDF library.

    The LaTeX log ends with "Output written on report_skeleton.pdf
    (12 pages, 250189 bytes)" -- that is the authoritative number and it
    needs no parser.
    """
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"Output written on .*?\((\d+) pages?", text)
        if m:
            return int(m.group(1))
    try:
        raw = pdf.read_bytes()
    except OSError:
        return None
    counts = [int(m) for m in re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)",
                                         raw)]
    if counts:
        return max(counts)
    text = raw.decode("latin-1", "replace")
    pages = len(re.findall(r"/Type\s*/Page[^s]", text))
    return pages or None


def main() -> int:
    if not (REPORT_DIR / TEX).is_file():
        print(f"找不到 {REPORT_DIR / TEX}")
        return 1

    exe, kind = find_compiler()
    if not exe:
        print(NO_LATEX)
        return 2

    print("编译报告 ...")
    for i in (1, 2):
        print(f"  第 {i} 遍")
        rc = compile_once(exe, kind)
        if rc not in (0, 1):
            print(f"  编译器返回 {rc}")
            break

    pdf = REPORT_DIR / "report_skeleton.pdf"
    if not pdf.is_file():
        print("\n没有生成 PDF。最后 15 行日志：")
        log = REPORT_DIR / "report_skeleton.log"
        if log.is_file():
            print("\n".join(log.read_text(encoding="utf-8",
                                          errors="replace").splitlines()[-15:]))
        return 3

    log = REPORT_DIR / "report_skeleton.log"
    errors = 0
    if log.is_file():
        errors = len(re.findall(r"^!", log.read_text(encoding="utf-8",
                                                      errors="replace"),
                                flags=re.M))
    pages = page_count(pdf, log)

    print()
    if errors == 0:
        print(f"完成：{pages} 页，0 个 LaTeX 错误。")
    else:
        print(f"完成：{pages} 页，但有 {errors} 个 LaTeX 错误 "
              f"-> report\\report_skeleton.log")
    print("课程要求：封面 1 页 + 正文最多 10 页 + 参考文献不限")
    if pages and pages > 12:
        print(f"注意：{pages} 页超过 12 页（正文上限 10 页），需要再压缩。")
    elif pages == 12:
        print("页数符合要求（封面 1 + 正文 10 + 参考文献 1）。")
    print(f"PDF: {pdf}")

    if os.name == "nt":
        os.startfile(str(pdf))          # noqa: S606  (Windows only)
    else:
        subprocess.run(["xdg-open", str(pdf)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
