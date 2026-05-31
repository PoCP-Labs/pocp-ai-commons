# Phase A public staging — verify env, then run staging acceptance (no dev-login).
param(
    [Parameter(Mandatory = $true)]
    [string]$ApiUrl
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Staging env check ==="
python backend/scripts/verify_staging_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Phase A staging acceptance @ $ApiUrl ==="
python backend/scripts/run_phase_a_acceptance.py $ApiUrl --staging --skip-optional
exit $LASTEXITCODE
