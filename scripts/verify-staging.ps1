# Phase A — verify backend/.env before public staging deploy.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
python backend/scripts/verify_staging_env.py @args
exit $LASTEXITCODE
