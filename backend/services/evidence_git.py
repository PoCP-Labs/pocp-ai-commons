"""Git commit evidence validation (TrustMyGit / OCTP integrity inspired)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from services.evidence import standardize_evidence_items

_GITHUB_COMMIT_URL = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/commit/(?P<sha>[a-f0-9]{7,40})",
    re.I,
)
_SHA_PATTERN = re.compile(r"^[a-f0-9]{7,40}$", re.I)


def _repo_root() -> Path | None:
    env_root = os.getenv("POCP_GIT_REPO_ROOT", "").strip()
    if env_root:
        path = Path(env_root)
        return path if path.exists() else None
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / ".git").exists():
        return candidate
    return None


def _extract_commit_refs(evidence: dict | None) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if not evidence:
        return refs

    for item in standardize_evidence_items(evidence):
        key = item.get("key", "")
        value = item.get("value")
        values: list[str] = []
        if isinstance(value, str):
            values = [value.strip()]
        elif isinstance(value, list):
            values = [str(v).strip() for v in value if v]

        for raw in values:
            match = _GITHUB_COMMIT_URL.search(raw)
            if match:
                refs.append(
                    {
                        "key": key,
                        "sha": match.group("sha"),
                        "owner": match.group("owner"),
                        "repo": match.group("repo"),
                        "source": "github_url",
                    }
                )
                continue
            if _SHA_PATTERN.match(raw):
                refs.append({"key": key, "sha": raw, "source": "sha"})

    return refs


def _verify_local_commit(sha: str, repo_root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", sha],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        ok = result.returncode == 0 and result.stdout.strip() == "commit"
        return {"ok": ok, "method": "local_git", "object_type": result.stdout.strip() or None}
    except Exception as exc:
        return {"ok": False, "method": "local_git", "reason": str(exc)}


def _verify_github_commit(owner: str, repo: str, sha: str, *, timeout: float = 5.0) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
        return {
            "ok": response.status_code == 200,
            "method": "github_api",
            "status_code": response.status_code,
        }
    except Exception as exc:
        return {"ok": False, "method": "github_api", "reason": str(exc)}


def validate_git_commits(evidence: dict | None) -> dict[str, Any]:
    refs = _extract_commit_refs(evidence)
    repo_root = _repo_root()
    checks: list[dict[str, Any]] = []

    for ref in refs:
        sha = ref["sha"]
        check: dict[str, Any] = {"key": ref["key"], "sha": sha, "source": ref["source"]}

        if repo_root is not None:
            local = _verify_local_commit(sha, repo_root)
            check.update(local)
            if local.get("ok"):
                checks.append(check)
                continue

        if ref.get("owner") and ref.get("repo"):
            remote = _verify_github_commit(ref["owner"], ref["repo"], sha)
            check.update(remote)
        elif not check.get("ok"):
            check.setdefault("ok", False)
            check.setdefault("reason", "commit_not_found_locally_and_no_github_context")

        checks.append(check)

    failed = [c for c in checks if not c.get("ok")]
    return {
        "checked_count": len(checks),
        "failed_count": len(failed),
        "all_ok": len(checks) > 0 and len(failed) == 0,
        "repo_root": str(repo_root) if repo_root else None,
        "checks": checks,
        "compat": "trustmygit-evidence-v0",
    }
