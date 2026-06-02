"""Generate prompt patch suggestion files when proposals are applied."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from meta_agents_spec import META_AGENT_BY_ID
from models.agent import Agent
from models.agent_studio import AgentStudioProposal

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PATCHES_DIR = _REPO_ROOT / "agents" / "patches"


def _agent_slug(entity_id: str) -> str:
    spec = META_AGENT_BY_ID.get(entity_id, {})
    return spec.get("slug") or entity_id.replace("pocp-agent-", "")


def build_patch_markdown(
    proposal: AgentStudioProposal,
    agent: Agent | None,
    *,
    actor_entity_id: str,
    evolution_version: int,
) -> str:
    config = (agent.config or {}) if agent else {}
    profile = config.get("learning_profile") or {}
    prompt_path = config.get("prompt_path") or f"agents/prompts/{_agent_slug(proposal.agent_entity_id)}.md"
    changes = proposal.proposed_changes or {}

    lines = [
        f"# Prompt patch suggestion — {proposal.title}",
        "",
        f"**Agent:** `{proposal.agent_entity_id}`",
        f"**Proposal:** `{proposal.id}`",
        f"**Applied by:** `{actor_entity_id}`",
        f"**Evolution version:** {evolution_version}",
        f"**Generated:** {datetime.utcnow().isoformat()}Z",
        "",
        "## Rationale",
        "",
        proposal.rationale or "_No rationale recorded._",
        "",
        "## Suggested edits",
        "",
        f"Review and merge into `{prompt_path}` manually (Anchor-H / Herald-0).",
        "",
    ]

    action = changes.get("action")
    if action == "improve":
        lines.extend(
            [
                "### Improve playbook",
                "",
                "- Add a **Failure recovery** section referencing this outcome evidence.",
                "- Tighten pre-merge checklist for the failing domain.",
                f"- Evidence keys: `{list((changes.get('evidence') or {}).keys())}`",
                "",
                "```markdown",
                "## Failure recovery (auto-suggested)",
                "",
                f"- Last failure context: {proposal.title}",
                "- Re-run tests listed in handoff before returning to Nexus-0.",
                "```",
                "",
            ]
        )
    elif action == "grow":
        lines.extend(
            [
                "### Grow capabilities",
                "",
                f"- Consider documenting mastery in `{changes.get('capability_hint', 'domain')}` in the agent prompt.",
                f"- Pass streak at apply time: {changes.get('pass_streak', 'n/a')}",
                "",
                "```markdown",
                "## Proven strengths (auto-suggested)",
                "",
                f"- Reliable at: {changes.get('capability_hint', 'see outcomes')}",
                "```",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Config tune",
                "",
                f"- Proposed changes JSON: `{changes}`",
                "",
            ]
        )

    if profile.get("growth_areas"):
        lines.extend(["## Growth areas (profile)", "", ", ".join(profile["growth_areas"]), ""])
    if profile.get("strengths"):
        lines.extend(["", "## Strengths (profile)", "", ", ".join(profile["strengths"]), ""])

    lines.extend(
        [
            "",
            "## Do not auto-apply",
            "",
            "PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,",
            "then run `python agents/sync_cursor_skills.py` if frontmatter changes.",
            "",
        ]
    )
    return "\n".join(lines)


def write_patch_suggestion_file(
    proposal: AgentStudioProposal,
    agent: Agent | None,
    *,
    actor_entity_id: str,
    evolution_version: int,
) -> dict:
    """Write markdown patch file under agents/patches/ (idempotent per proposal id)."""
    _PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    slug = _agent_slug(proposal.agent_entity_id)
    short = proposal.id.split("-")[0] if "-" in proposal.id else proposal.id[:8]
    filename = f"{slug}-{short}.md"
    path = _PATCHES_DIR / filename
    content = build_patch_markdown(
        proposal,
        agent,
        actor_entity_id=actor_entity_id,
        evolution_version=evolution_version,
    )
    path.write_text(content, encoding="utf-8")
    rel = path.relative_to(_REPO_ROOT).as_posix()
    return {
        "patch_file": rel,
        "patch_absolute": str(path),
        "patch_preview_lines": len(content.splitlines()),
    }
