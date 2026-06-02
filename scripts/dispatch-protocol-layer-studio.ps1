#Requires -Version 5.1
<#
.SYNOPSIS
  Dispatch Protocol Layer mission to Agent Studio (Issues PL-1..PL-10 → PA handoffs).

.EXAMPLE
  .\scripts\dispatch-protocol-layer-studio.ps1
  .\scripts\dispatch-protocol-layer-studio.ps1 -CreateIssues -CursorTick
  .\scripts\dispatch-protocol-layer-studio.ps1 -ApiBase "http://127.0.0.1:8000" -SuperTick
#>
param(
    [string]$ApiBase = $env:POCP_API_BASE,
    [switch]$CreateIssues,
    [switch]$IssuesDryRun,
    [switch]$CursorTick,
    [switch]$SuperTick,
    [string]$Repo = $(if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "PoCP-Labs/pocp-ai-commons" })
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root "backend\scripts\dispatch_protocol_layer_studio.py"

$args = @()
if ($ApiBase) { $args += @("--api", $ApiBase) }
if ($CreateIssues) { $args += "--create-issues" }
if ($IssuesDryRun) { $args += "--issues-dry-run" }
if ($CursorTick) { $args += "--cursor-tick" }
if ($SuperTick) { $args += "--super-tick" }
$args += @("--repo", $Repo)

python $Py @args
exit $LASTEXITCODE
