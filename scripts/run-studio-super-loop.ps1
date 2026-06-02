# Nexus super-loop on Windows host (plan + Cursor + PDCA + heal). Docker backend stays API-only.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
}
if (-not $env:POCP_REPO_ROOT) {
  $env:POCP_REPO_ROOT = $Root
}
if (-not $env:BACKEND_URL) {
  $env:BACKEND_URL = "http://localhost:8008"
}
if (-not $env:POCP_CURSOR_AUTOMATION) {
  $env:POCP_CURSOR_AUTOMATION = "true"
}
if (-not $env:POCP_NEXUS_SUPER_LOOP_HOST) {
  $env:POCP_NEXUS_SUPER_LOOP_HOST = "true"
}

Write-Host "=== Super-loop pre-flight (Python 3.12+) ==="
py -3.12 backend/scripts/check_studio_super_loop.py
if ($LASTEXITCODE -ne 0) {
  exit 1
}

Write-Host ""
Write-Host "POCP_REPO_ROOT=$env:POCP_REPO_ROOT"
Write-Host "BACKEND_URL=$env:BACKEND_URL"
Write-Host ""
py -3.12 backend/scripts/run_studio_super_loop_worker.py
