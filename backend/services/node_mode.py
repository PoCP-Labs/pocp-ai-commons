"""Node operating mode — full participant vs read-only federation mirror."""

import os

MODE_FULL = "full"
MODE_READ_ONLY_MIRROR = "read_only_mirror"

_WRITE_PREFIXES_BLOCKED_IN_MIRROR = (
    "/api/v1/entities",
    "/api/v1/tasks",
    "/api/v1/contributions",
    "/api/v1/organizations",
    "/api/v1/skills",
    "/api/v1/agents",
    "/api/v1/invocations",
    "/api/v1/ai/chat",
)

_WRITE_PREFIXES_ALLOWED_IN_MIRROR = (
    "/api/v1/auth/",
    "/api/v1/federation/sync",
    "/api/v1/federation/import",
    "/api/v1/federation/import-proof",
)


def node_mode() -> str:
    mode = os.getenv("POCP_NODE_MODE", MODE_FULL).strip().lower()
    if mode in (MODE_FULL, MODE_READ_ONLY_MIRROR):
        return mode
    return MODE_FULL


def is_read_only_mirror() -> bool:
    return node_mode() == MODE_READ_ONLY_MIRROR


def is_write_allowed(path: str, method: str) -> bool:
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return True
    if not is_read_only_mirror():
        return True

    for prefix in _WRITE_PREFIXES_ALLOWED_IN_MIRROR:
        if path.startswith(prefix):
            return True

    for prefix in _WRITE_PREFIXES_BLOCKED_IN_MIRROR:
        if path.startswith(prefix):
            return False

    return True
