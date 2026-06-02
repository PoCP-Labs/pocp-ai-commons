"""Platform health probes for Nexus super-automation (self-healing dispatch)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def probe_database(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True, "detail": "postgres ping ok"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


def probe_api_health() -> dict[str, Any]:
    base = (os.getenv("BACKEND_URL") or "http://127.0.0.1:8008").rstrip("/")
    try:
        import httpx

        resp = httpx.get(f"{base}/health", timeout=10.0)
        if resp.status_code != 200:
            return {"ok": False, "detail": f"HTTP {resp.status_code}", "base": base}
        data = resp.json()
        if data.get("service") != "pocp-ai-commons":
            return {"ok": False, "detail": f"wrong service: {data.get('service')}", "base": base}
        db_st = (data.get("database") or {}).get("status")
        if db_st and db_st != "ok":
            return {"ok": False, "detail": f"database status={db_st}", "base": base}
        return {"ok": True, "detail": "health ok", "base": base, "version": data.get("version")}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500], "base": base}


def probe_platform(db: Session) -> dict[str, Any]:
    """Aggregate platform health for super-loop repair decisions."""
    db_probe = probe_database(db)
    api_probe = probe_api_health()
    ok = db_probe.get("ok") and api_probe.get("ok")
    issues: list[str] = []
    if not db_probe.get("ok"):
        issues.append(f"database: {db_probe.get('detail')}")
    if not api_probe.get("ok"):
        issues.append(f"api: {api_probe.get('detail')}")
    return {
        "ok": ok,
        "database": db_probe,
        "api": api_probe,
        "issues": issues,
    }
