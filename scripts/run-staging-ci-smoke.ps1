# CI-equivalent staging OAuth smoke (ENABLE_DEV_LOGIN=false, no real GitHub secrets).
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Base = "http://127.0.0.1:$Port"
$Db = "sqlite:///$($Root -replace '\\','/')/backend/data/pocp_staging_ci_local.db"

Write-Host "=== Staging env example check ==="
python backend/scripts/verify_staging_env.py --check-example
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Staging compose profile check ==="
python -c @"
import pathlib
text = pathlib.Path('docker-compose.staging.yml').read_text(encoding='utf-8')
for needle in ('ENABLE_DEV_LOGIN', '\"false\"', 'APP_ENV', 'staging'):
    assert needle in text, needle
print('docker-compose.staging.yml OK')
"@

Write-Host ""
Write-Host "=== Start API @ $Base (staging profile) ==="
$env:DATABASE_URL = $Db
$env:POCP_WAIT_FOR_DB = "false"
$env:POCP_FULL_SEED = "true"
$env:APP_ENV = "staging"
$env:ENABLE_DEV_LOGIN = "false"
$env:JWT_SECRET = "local-staging-ci-jwt-not-for-production"
$env:GITHUB_CLIENT_ID = "local-staging-oauth-client"
$env:GITHUB_CLIENT_SECRET = "local-staging-oauth-secret"
$env:GITHUB_OAUTH_CALLBACK_URL = "$Base/api/v1/auth/github/callback"
$env:BACKEND_URL = $Base
$env:FRONTEND_URL = "http://127.0.0.1:3000"
$env:POCP_REQUIRE_RECEIPT_SIGNATURE = "true"
$env:POCP_SIGN_COMPUTE_RECEIPTS = "true"

New-Item -ItemType Directory -Force -Path backend/data | Out-Null
$job = Start-Job -ScriptBlock {
    param($Root, $Port)
    Set-Location (Join-Path $Root "backend")
    uvicorn main:app --host 127.0.0.1 --port $Port
} -ArgumentList $Root, $Port

try {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-WebRequest -Uri "$Base/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "API did not become healthy at $Base"
    }

    Write-Host ""
    Write-Host "=== Phase A staging acceptance ==="
    python backend/scripts/run_phase_a_acceptance.py $Base --staging --skip-optional
    exit $LASTEXITCODE
} finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
