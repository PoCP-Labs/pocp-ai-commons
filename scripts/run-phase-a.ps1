# Phase A — one-command local acceptance (single node or federation).
param(
    [switch]$Federation
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if ($Federation) {
    Write-Host "Starting federation stack (node-a :8100, node-b :8101)…"
    docker compose -f docker-compose.federation.yml up -d --build
    $Base = "http://127.0.0.1:8100"
    $NodeB = "http://127.0.0.1:8101"
    $FedArgs = @("--federation", $NodeB)
} else {
    Write-Host "Starting single-node stack (:8000 API, :3000 UI)…"
    docker compose up -d --build
    $Base = "http://127.0.0.1:8000"
    $FedArgs = @()
}

Write-Host "Waiting for API health at $Base (first boot may take up to 6 min)…"
$ready = $false
for ($i = 1; $i -le 180; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$Base/health" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Timeout waiting for $Base/health" }
Write-Host "API ready."

if ($Federation) {
    for ($i = 1; $i -le 180; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "$NodeB/health" -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) { Write-Host "Node B ready."; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
}

$Acceptance = Join-Path $Root "backend\scripts\run_phase_a_acceptance.py"
& python $Acceptance $Base @FedArgs
exit $LASTEXITCODE
