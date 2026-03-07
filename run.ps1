param(
  [Parameter(Mandatory = $true)]
  [string]$Request,

  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSCommandPath
Set-Location $repoRoot

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$py = if ($pythonCmd) { $pythonCmd.Source } else { $null }
if (-not $py) {
  $pyCmd = Get-Command py -ErrorAction SilentlyContinue
  $py = if ($pyCmd) { $pyCmd.Source } else { $null }
  if (-not $py) {
    throw "python not found"
  }
  & $py -3 -c "import sys; print(sys.executable)" | Out-Null
  $py = "py"
  $pyArgsPrefix = @("-3")
} else {
  $pyArgsPrefix = @()
}

& $py @pyArgsPrefix -c "import sys; sys.exit('Python >= 3.10 required' if sys.version_info < (3,10) else 0)" | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($env:STOCKDAILY_NO_VENV -ne "1") {
  $venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) {
    & $py @pyArgsPrefix -m venv .venv | Out-Null
  }
  $py = $venvPy
  $pyArgsPrefix = @()
}

$env:PYTHONPATH = Join-Path $repoRoot "src"

$req = Get-Content -Raw -Path $Request | ConvertFrom-Json

$date = [string]$req.date
if ([string]::IsNullOrWhiteSpace($date)) {
  throw "request.date is required"
}

$positions = $req.positions
if (-not $positions -or $positions.Count -eq 0) {
  throw "request.positions must be a non-empty array"
}

$dbPath = if ($req.db_path) { [string]$req.db_path } else { "portfolio.db" }
$outDir = if ($req.out_dir) { [string]$req.out_dir } else { "daily_reports" }

if ($req.backfill) {
  $start = [string]$req.backfill.start
  $end = [string]$req.backfill.end
  if ([string]::IsNullOrWhiteSpace($start) -or [string]::IsNullOrWhiteSpace($end)) {
    throw "request.backfill.start/end is required"
  }
} else {
  $start = $date
  $end = $date
}

$symbols = New-Object System.Collections.Generic.List[string]
foreach ($p in $positions) {
  $s = [string]$p
  if (-not $s.Contains(":")) { throw "positions item must be asset_id:quantity" }
  $assetId = $s.Split(":", 2)[0].Trim()
  if ([string]::IsNullOrWhiteSpace($assetId)) { throw "asset_id is required" }
  $up = $assetId.ToUpperInvariant()
  if ($up -eq "BTC" -or $up -eq "ETH") { $assetId = $up }
  $isCn = $assetId -match "^\d{6}$"
  $isTicker = $assetId -match "^[A-Za-z0-9.\-]+$"
  if (-not $isCn -and -not $isTicker) { throw "invalid asset_id: $assetId" }
  $symbols.Add($assetId)
}

$ingestArgs = @("--db", $dbPath, "public-backfill", "--start", $start, "--end", $end, "--symbols") + $symbols.ToArray()
$reportArgs = @("--db", $dbPath, "daily", "--date", $date, "--out-dir", $outDir)
foreach ($p in $positions) {
  $reportArgs += @("--position", [string]$p)
}

if ($DryRun) {
  Write-Output ($py + " -m stock.ingest " + ($ingestArgs -join " "))
  Write-Output ($py + " -m stock.report " + ($reportArgs -join " "))
  exit 0
}

& $py -m stock.ingest @ingestArgs | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$reportPath = & $py -m stock.report @reportArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -Path $reportPath)) {
  throw "report file not found: $reportPath"
}

Write-Output $reportPath
