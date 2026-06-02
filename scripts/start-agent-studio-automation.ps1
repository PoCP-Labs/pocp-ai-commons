# Start Agent Studio full automation (Windows host super-loop worker).
# Docker: API + Postgres only. Cursor + PDCA runs here.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "agent-studio-automation.log"
$PidFile = Join-Path $LogDir "agent-studio-automation.pid"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (Test-Path $PidFile) {
  $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
  if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
    Write-Host "Agent Studio automation already running (PID $oldPid). Log: $LogFile"
    exit 0
  }
}

Write-Host "=== 1/4 Docker stack (postgres + backend + frontend) ==="
docker compose up -d postgres backend frontend
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "=== 2/4 Wait for API health ==="
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:8008/health" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $healthy = $true; break }
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $healthy) {
  Write-Warning "Backend not healthy yet; worker may retry on first tick."
}

Write-Host "=== 3/4 Restart backend (apply host-mode env) ==="
docker compose restart backend | Out-Null

$env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
$env:POCP_REPO_ROOT = $Root
$env:BACKEND_URL = "http://localhost:8008"
$env:POCP_CURSOR_AUTOMATION = "true"
$env:POCP_NEXUS_SUPER_LOOP_HOST = "true"
$env:POCP_NEXUS_SUPER_LOOP = "false"
$env:POCP_NEXUS_AUTOPILOT = "true"
$env:POCP_STUDIO_AUTO_EVOLVE = "true"

Write-Host "=== 4/4 Pre-flight + start host worker ==="
py -3.12 backend/scripts/check_studio_super_loop.py
if ($LASTEXITCODE -ne 0) { exit 1 }

$workerScript = Join-Path $Root "scripts\run-studio-super-loop.ps1"
$proc = Start-Process -FilePath "powershell.exe" `
  -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $workerScript `
  -WorkingDirectory $Root `
  -WindowStyle Minimized `
  -RedirectStandardOutput $LogFile `
  -RedirectStandardError $LogFile `
  -PassThru

$proc.Id | Set-Content $PidFile
Write-Host ""
Write-Host "Agent Studio automation STARTED"
Write-Host "  PID:      $($proc.Id)"
Write-Host "  Log:      $LogFile"
Write-Host "  UI:       http://localhost:3000/?tab=studio"
Write-Host "  API:      http://localhost:8008/api/v1/agent-studio/automation/status"
Write-Host ""
Write-Host "Stop: .\scripts\stop-agent-studio-automation.ps1"
