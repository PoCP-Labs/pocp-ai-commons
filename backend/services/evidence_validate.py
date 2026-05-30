"""Non-blocking evidence URL checks before verification.

Inspired by Meritocrab / OCTP integrity layers — surface broken links early.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from services.evidence import standardize_evidence_items

_URL_PATTERN = re.compile(r"^https?://", re.I)


def _collect_urls(evidence: dict | None) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    for item in standardize_evidence_items(evidence):
        value = item.get("value")
        key = item.get("key", "url")
        if isinstance(value, str) and _URL_PATTERN.match(value.strip()):
            urls.append((key, value.strip()))
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and _URL_PATTERN.match(entry.strip()):
                    urls.append((key, entry.strip()))
    return urls


def validate_evidence_urls(evidence: dict | None, *, timeout: float = 5.0) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for key, url in _collect_urls(evidence):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            checks.append({"key": key, "url": url, "ok": False, "reason": "unsupported_scheme"})
            continue
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.head(url)
                if response.status_code >= 400:
                    response = client.get(url)
                ok = response.status_code < 400
                checks.append(
                    {
                        "key": key,
                        "url": url,
                        "ok": ok,
                        "status_code": response.status_code,
                    }
                )
        except Exception as exc:
            checks.append({"key": key, "url": url, "ok": False, "reason": str(exc)})

    failed = [c for c in checks if not c.get("ok")]
    return {
        "checked_count": len(checks),
        "failed_count": len(failed),
        "all_ok": len(checks) > 0 and len(failed) == 0,
        "checks": checks,
        "compat": "octp-integrity-v0",
    }


def validate_evidence_full(evidence: dict | None, *, timeout: float = 5.0) -> dict[str, Any]:
    """Combined URL + git commit integrity checks."""
    from services.evidence_git import validate_git_commits

    url_report = validate_evidence_urls(evidence, timeout=timeout)
    git_report = validate_git_commits(evidence)
    failed = url_report.get("failed_count", 0) + git_report.get("failed_count", 0)
    checked = url_report.get("checked_count", 0) + git_report.get("checked_count", 0)
    return {
        "checked_count": checked,
        "failed_count": failed,
        "all_ok": checked > 0 and failed == 0,
        "urls": url_report,
        "git": git_report,
        "compat": "octp-integrity-v0",
    }
