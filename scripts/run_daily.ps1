$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

Set-Location $repoRoot

python -m stock.ingest --db portfolio.db public-daily
python -m stock.report --db portfolio.db daily --out-dir daily_reports --latest-name latest_report.md
