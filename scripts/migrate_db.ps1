$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

Set-Location $repoRoot

python -m stock.ingest --db portfolio.db migrate-db --sources portfolio.db stock_tracker.db stock_portfolio.db
