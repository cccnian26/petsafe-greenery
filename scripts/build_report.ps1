# 一键编译报告（Windows PowerShell）
#
#   powershell -ExecutionPolicy Bypass -File scripts\build_report.ps1
#
# 做三件事：
#   1. 找到 pdflatex（或 latexmk），没有就给出明确的安装指引；
#   2. 连续编译两遍（第二遍用于交叉引用和参考文献）；
#   3. 报告错误数、页数，并自动打开 PDF。
#
# 不需要 VS Code 的 LaTeX 扩展，也不需要 latexmk。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$reportDir = Join-Path $root "report"
$tex = Join-Path $reportDir "report_skeleton.tex"

if (-not (Test-Path $tex)) {
    Write-Host "找不到 report_skeleton.tex，请确认你在项目根目录运行。" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------- 找到编译器
$pdflatex = Get-Command pdflatex -ErrorAction SilentlyContinue
$latexmk  = Get-Command latexmk  -ErrorAction SilentlyContinue

if (-not $pdflatex -and -not $latexmk) {
    Write-Host @"
没有找到 LaTeX 编译器。

最快的一条路（不用装任何东西）：
  1. 打开 https://overleaf.com 并注册（免费）
  2. New Project -> Upload Project -> 把整个 petsafe-greenery 文件夹压成 zip 传上去
  3. Main document 选 report/report_skeleton.tex
  4. 点 Recompile，右上角就能预览，右下角下载 PDF

要本机编译的话，装 MiKTeX（免费）：https://miktex.org/download
  装的时候勾选 "Install missing packages on the fly"，之后重新开终端再跑本脚本。
"@ -ForegroundColor Yellow
    exit 2
}

Set-Location $reportDir

# ---------------------------------------------------------------- 编译
function Invoke-LaTeX([string]$exe, [string[]]$arguments) {
    Write-Host "  > $exe $($arguments -join ' ')" -ForegroundColor DarkGray
    & $exe @arguments | Out-Null
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
        Write-Host "  编译器返回 $LASTEXITCODE" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "编译报告..." -ForegroundColor Cyan
if ($latexmk) {
    Invoke-LaTeX $latexmk.Source @("-pdf", "-interaction=nonstopmode", "report_skeleton.tex")
    Invoke-LaTeX $latexmk.Source @("-pdf", "-interaction=nonstopmode", "report_skeleton.tex")
} else {
    Invoke-LaTeX $pdflatex.Source @("-interaction=nonstopmode", "report_skeleton.tex")
    Invoke-LaTeX $pdflatex.Source @("-interaction=nonstopmode", "report_skeleton.tex")
}

# ---------------------------------------------------------------- 检查结果
$log = Join-Path $reportDir "report_skeleton.log"
$pdf = Join-Path $reportDir "report_skeleton.pdf"

if (-not (Test-Path $pdf)) {
    Write-Host "没有生成 PDF。错误信息在 report\report_skeleton.log 的最后几行。" -ForegroundColor Red
    Get-Content $log -Tail 15
    exit 3
}

$errors = 0
if (Test-Path $log) {
    $errors = (Select-String -Path $log -Pattern "^!" -AllMatches).Count
}
$pages = "?"
try {
    $text = Get-Content $pdf -Raw -Encoding Byte -ErrorAction SilentlyContinue
    $m = [regex]::Match([System.Text.Encoding]::ASCII.GetString($text), "/Type\s*/Pages.*?/Count\s+(\d+)")
    if ($m.Success) { $pages = $m.Groups[1].Value }
} catch { }

Write-Host ""
if ($errors -eq 0) {
    Write-Host "完成：$pages 页，0 个 LaTeX 错误。" -ForegroundColor Green
} else {
    Write-Host "完成：$pages 页，但有 $errors 个 LaTeX 错误，看 report\report_skeleton.log。" -ForegroundColor Yellow
}
Write-Host "课程要求：封面 1 页 + 正文最多 10 页 + 参考文献不限"
Write-Host "PDF: $pdf"
Write-Host ""

if (Test-Path $pdf) {
    Start-Process $pdf
}
