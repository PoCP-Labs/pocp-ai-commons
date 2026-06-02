# Visible Agent Studio + Cursor trial (streams to this terminal)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:POCP_STUDIO_VERBOSE = "true"
$env:POCP_CURSOR_WORKER_ONCE = "true"
$env:POCP_CURSOR_AUTOMATION = "true"
if (-not $env:POCP_REPO_ROOT) { $env:POCP_REPO_ROOT = $Root }
if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
}

Write-Host ""
Write-Host "=== Agent Studio visible trial ===" -ForegroundColor Cyan
Write-Host "You will see: Nexus dispatch -> handoff pick -> Cursor streaming output"
Write-Host ""

# cursor-sdk requires Python 3.12+ (os.get_blocking)
py -3.12 backend/scripts/run_studio_cursor_worker.py --verbose --once
