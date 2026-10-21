[CmdletBinding()]
param(
    [switch]$NoRefresh,
    [switch]$FullRefit
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "scripts\run_momentum_daily.py"
$LogDirectory = Join-Path $ProjectRoot "live\logs"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found at $Python. Recreate .venv and install requirements.txt and requirements-momentum.txt."
}

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Log = Join-Path $LogDirectory "momentum-$Timestamp.log"
$RunnerArgs = @()
if ($NoRefresh) { $RunnerArgs += "--no-refresh" }
if ($FullRefit) { $RunnerArgs += "--full-refit" }

Push-Location $ProjectRoot
try {
    & $Python $Runner @RunnerArgs *>&1 | Tee-Object -FilePath $Log
    if ($LASTEXITCODE -ne 0) {
        throw "Momentum daily runner failed with exit code $LASTEXITCODE. See $Log"
    }
}
finally {
    Pop-Location
}
