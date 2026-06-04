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

if (-not (Test-Path "docker-compose.staging.yml")) {
    Write-Error "FAIL: missing docker-compose.staging.yml"
    exit 1
}

Write-Host ""
Write-Host "=== Phase A staging acceptance @ $ApiUrl ==="
python backend/scripts/run_phase_a_acceptance.py $ApiUrl --staging --skip-optional
exit $LASTEXITCODE
