$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "logs\agent-studio-automation.pid"
if (-not (Test-Path $PidFile)) {
  Write-Host "No PID file — automation may not be running."
  exit 0
}
$workerPid = [int](Get-Content $PidFile)
$proc = Get-Process -Id $workerPid -ErrorAction SilentlyContinue
if ($proc) {
  Stop-Process -Id $workerPid -Force
  Write-Host "Stopped Agent Studio automation (PID $workerPid)."
} else {
  Write-Host "Process $workerPid not found."
}
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
