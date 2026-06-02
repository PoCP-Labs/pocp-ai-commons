# Agent Studio → Cursor full automation (run on Windows host, not inside Docker).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
}
if (-not $env:POCP_REPO_ROOT) {
  $env:POCP_REPO_ROOT = $Root
}
if (-not $env:POCP_CURSOR_AUTOMATION) {
  $env:POCP_CURSOR_AUTOMATION = "true"
}

Write-Host "=== Pre-flight check (Python 3.12+) ==="
py -3.12 backend/scripts/check_studio_cursor.py
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Fix the items above, then re-run this script."
  exit 1
}

Write-Host ""
Write-Host "POCP_REPO_ROOT=$env:POCP_REPO_ROOT"
Write-Host ""
py -3.12 backend/scripts/run_studio_cursor_worker.py
