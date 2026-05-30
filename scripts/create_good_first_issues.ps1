# Create Good First Issues on GitHub from curated list.
# Requires: gh CLI (https://cli.github.com/) and gh auth login

param(
    [string]$Repo = "PoCP-Labs/pocp-ai-commons"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) not found. Install from https://cli.github.com/"
}

gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Run 'gh auth login' first."
}

$labels = @(
    @{name="good first contribution"; color="7057ff"; desc="Good for newcomers"},
    @{name="documentation"; color="0075ca"},
    @{name="backend"; color="d73a4a"},
    @{name="frontend"; color="fbca04"},
    @{name="ai-verifier"; color="1d76db"},
    @{name="testing"; color="006b75"},
    @{name="anti-abuse"; color="b60205"},
    @{name="graph"; color="5319e7"},
    @{name="entity"; color="c5def5"},
    @{name="skill"; color="0e8a16"},
    @{name="review"; color="e99695"}
)
foreach ($l in $labels) {
    gh label create $l.name --repo $Repo --color $l.color --description ($l.desc ?? "") --force 2>$null | Out-Null
}

$issues = @(
    @{
        Title = "[Docs] Improve README clarity for first-time visitors"
        Body = @"
Make README easier for newcomers.

Focus:
- What is PoCP AI Commons?
- What is the first loop?
- What are AI Credits?
- What is NOT in v0.1?

See GOOD_FIRST_ISSUES.md #1
"@
        Labels = "documentation,good first contribution"
    },
    @{
        Title = "[Docs] Add FAQ: Is PoCP a token project?"
        Body = @"
Write a short FAQ explaining:
- PoCP does not start with a token
- AI Credits are usage rights, not speculative assets
- Contribution comes before financialization

See GOOD_FIRST_ISSUES.md #3
"@
        Labels = "documentation,good first contribution"
    },
    @{
        Title = "[Backend] Add OpenAI Verifier tests"
        Body = @"
Test OpenAI Verifier: prompt build, JSON parse, safe fallback, never auto-approves.

See GOOD_FIRST_ISSUES.md #5
"@
        Labels = "backend,ai-verifier,good first contribution"
    },
    @{
        Title = "[Backend] Add AI Credits burn tests"
        Body = @"
Test: chat consumes credits, insufficient credits blocks usage, usage log + transaction created.

See GOOD_FIRST_ISSUES.md #7
"@
        Labels = "backend,testing,good first contribution"
    },
    @{
        Title = "[Backend] Add anti-abuse test cases"
        Body = @"
Test: missing evidence rejected, daily limits, self-approval blocked.

See GOOD_FIRST_ISSUES.md #8
"@
        Labels = "backend,anti-abuse,testing"
    },
    @{
        Title = "[Frontend] Improve AI Chat UI"
        Body = @"
Enhance AI Chat: credits display, cost per message, insufficient credits UX, usage history polish.

See GOOD_FIRST_ISSUES.md #9
"@
        Labels = "frontend,good first contribution"
    },
    @{
        Title = "[Frontend] Improve Contribution Graph visualization"
        Body = @"
Add node types for Contribution, AI Verifier, Human Reviewer, Ledger in graph explorer.

See GOOD_FIRST_ISSUES.md #10
"@
        Labels = "frontend,graph,good first contribution"
    },
    @{
        Title = "[Frontend] Add Skill detail page"
        Body = @"
Dedicated Skill profile: reputation, invocations, related contributions.

See GOOD_FIRST_ISSUES.md #11 (Skill variant)
"@
        Labels = "frontend,entity,good first contribution"
    },
    @{
        Title = "[Skill] Define Study Helper Skill spec"
        Body = @"
Define Study Helper Skill: purpose, inputs, outputs, verification rubric.

See GOOD_FIRST_ISSUES.md #12
"@
        Labels = "skill,good first contribution"
    },
    @{
        Title = "[Review] Review anti-abuse rules and error messages"
        Body = @"
Review anti_abuse.py rules for Sprint Alpha pilot readiness.

See DEV-TASKS.md Review Tasks
"@
        Labels = "review,anti-abuse"
    }
)

$existing = gh issue list --repo $Repo --limit 200 --json title | ConvertFrom-Json
$existingTitles = $existing | ForEach-Object { $_.title }

$created = 0
foreach ($issue in $issues) {
    if ($existingTitles -contains $issue.Title) {
        Write-Host "SKIP (exists): $($issue.Title)"
        continue
    }
    gh issue create --repo $Repo --title $issue.Title --body $issue.Body --label $issue.Labels
    Write-Host "CREATED: $($issue.Title)"
    $created++
}

Write-Host "`nDone. Created $created new issue(s)."
