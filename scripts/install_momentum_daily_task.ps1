[CmdletBinding()]
param(
    [string]$TaskName = "Momentum Strategy Daily Update",
    [string]$LocalRunTime = "09:30"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DailyScript = Join-Path $ProjectRoot "scripts\run_momentum_daily.ps1"

if (-not (Test-Path -LiteralPath $DailyScript)) {
    throw "Daily runner not found at $DailyScript"
}

$At = [datetime]::Today.Add([timespan]::Parse($LocalRunTime))
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$DailyScript`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Refresh Yahoo daily bars, extend GARCH-t forecasts, and update the momentum strategy paper weights." `
    -Force

Write-Host "Installed '$TaskName' for $LocalRunTime local time."
Write-Host "For Singapore time, 09:30 is after the US close. The runner drops any final date lacking a US or SGX anchor bar."
