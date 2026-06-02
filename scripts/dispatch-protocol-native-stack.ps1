# Dispatch protocol_native_stack mission + optional Cursor tick (Python 3.12+)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = "py", "-3.12"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { $py = "python" }
& @py backend/scripts/dispatch_protocol_native_stack_studio.py @args
