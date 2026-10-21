<#
Run from PowerShell:
  .\scripts\start_ensemble_web_app.ps1
  .\scripts\start_ensemble_web_app.ps1 -Mode research
  .\scripts\start_ensemble_web_app.ps1 -InstallDependencies

Keep this terminal open while using the web app. Ctrl+C stops the server.
#>
[CmdletBinding()]
param(
    [ValidateSet('demo', 'research')]
    [string]$Mode = 'demo',
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [switch]$InstallDependencies
)

$ErrorActionPreference = 'Stop'
$ensembleRoot = Split-Path -Parent $PSScriptRoot
$ensemblePython = Join-Path $ensembleRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ensemblePython)) {
    throw 'Create the environment first from the repository root: py -3 -m venv .venv'
}

Push-Location -LiteralPath $ensembleRoot
try {
    if ($InstallDependencies) {
        & $ensemblePython -m pip install -r requirements-fund.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    if ($Mode -eq 'research') {
        & $ensemblePython -m fund_agents --config config/fund_agents.research.json --as-of 2026-10-16 --prices data/cache/asset_prices.csv --benchmark-prices data/cache/benchmark_SPY.csv --sectors data/cache/full_universe_sectors.csv
    } else {
        & $ensemblePython -m fund_agents
    }
    if ($LASTEXITCODE -ne 0) {
        throw 'The fund cycle did not complete. Read the INPUT_HOLD or risk message above before presenting the result.'
    }
    Write-Host "Open http://127.0.0.1:$Port/#overview"
    Write-Host 'Keep this terminal open. Ctrl+C stops the read-only dashboard.'
    & $ensemblePython -m fund_agents.dashboard --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard startup failed; choose another -Port if the port is occupied.' }
} finally {
    Pop-Location
}
