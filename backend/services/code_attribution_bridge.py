"""Bridge code attribution registry into contribution proof packets.

Inspired by drdeeks/contributor-attribution — surface builder impact alongside contributions.
"""

from __future__ import annotations

from typing import Any

from services.code_attribution import list_builders, match_builders_for_path, load_registry

_PATH_HINT_KEYS = ("path", "file", "artifact", "commit", "diff", "pull_request", "repo_path")


def _extract_path_hints(evidence: dict | None) -> list[str]:
    hints: list[str] = []
    if not evidence:
        return hints

    for key, value in evidence.items():
        if key.startswith("_"):
            continue
        key_lower = key.lower()
        if key_lower in _PATH_HINT_KEYS and isinstance(value, str) and value.strip():
            hints.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and ("/" in item or "\\" in item):
                    hints.append(item.strip())

    return list(dict.fromkeys(hints))


def build_code_attribution_context(evidence: dict | None) -> dict[str, Any]:
    """Summarize registry matches for paths referenced in contribution evidence."""
    hints = _extract_path_hints(evidence)
    builders_index = {b["slug"]: b for b in list_builders()}
    matches: list[dict[str, Any]] = []
    builder_totals: dict[str, dict[str, Any]] = {}

    for hint in hints:
        normalized = hint.replace("\\", "/").lstrip("./")
        slugs = match_builders_for_path(normalized)
        if not slugs and "/" not in normalized:
            continue
        entry = {"path_hint": hint, "normalized_path": normalized, "builders": []}
        for slug in slugs:
            spec = builders_index.get(slug, {"slug": slug})
            entry["builders"].append(
                {
                    "slug": slug,
                    "display_name": spec.get("display_name", slug),
                    "entity_id": spec.get("entity_id"),
                    "entity_type": spec.get("entity_type"),
                    "roles": spec.get("roles", []),
                    "status": spec.get("status"),
                }
            )
            bucket = builder_totals.setdefault(
                slug,
                {
                    "slug": slug,
                    "display_name": spec.get("display_name", slug),
                    "entity_id": spec.get("entity_id"),
                    "matched_paths": [],
                },
            )
            bucket["matched_paths"].append(normalized)
        if entry["builders"]:
            matches.append(entry)

    registry = load_registry()
    return {
        "registry_spec_version": registry.get("spec_version", "0.1"),
        "path_hints": hints,
        "matched_paths": matches,
        "builders_involved": list(builder_totals.values()),
        "bridge_compat": "contributor-attribution-v0",
    }
