# One verbose super-loop tick (see Nexus + Cursor output in terminal).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:POCP_SUPER_LOOP_WORKER_ONCE = "true"
$env:POCP_STUDIO_VERBOSE = "true"
if (-not $env:POCP_REPO_ROOT) { $env:POCP_REPO_ROOT = $Root }
if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
}
if (-not $env:BACKEND_URL) { $env:BACKEND_URL = "http://localhost:8008" }
if (-not $env:POCP_NEXUS_SUPER_LOOP_HOST) { $env:POCP_NEXUS_SUPER_LOOP_HOST = "true" }

py -3.12 backend/scripts/check_studio_super_loop.py
if ($LASTEXITCODE -ne 0) { exit 1 }
py -3.12 backend/scripts/run_studio_super_loop_worker.py --verbose --once
