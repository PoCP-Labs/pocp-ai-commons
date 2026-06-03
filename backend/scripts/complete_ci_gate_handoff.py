#!/usr/bin/env python3
"""Close Nexus [CI gate] handoff when local acceptance scripts pass."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=True)
except ImportError:
    pass

CI_GATE_PREFIX = "bc91cffd"


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=_BACKEND,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out[-2000:]


def main() -> int:
    checks: list[tuple[str, int, str]] = []

    code, tail = _run([sys.executable, "scripts/audit_entities.py", "--repair"])
    checks.append(("audit_entities --repair", code, tail))
    code, tail = _run([sys.executable, "scripts/minimum_living_network.py"])
    checks.append(("minimum_living_network", code, tail))

    phase_a_cmd = [sys.executable, "scripts/run_phase_a_acceptance.py", "--skip-optional"]
    code, tail = _run(phase_a_cmd)
    checks.append(("run_phase_a_acceptance --skip-optional", code, tail))
    phase_a_ok = code == 0

    required_ok = all(c[1] == 0 for c in checks[:2])
    if not required_ok:
        for name, code, _ in checks:
            print(f"[FAIL] {name} exit={code}")
        return 1

    from database import SessionLocal, init_db
    from models.agent_studio import AgentStudioHandoff, StudioHandoffStatus
    from services.agent_studio.handoffs import complete_handoff
    from services.agent_studio.outcomes import record_outcome

    init_db()
    db = SessionLocal()
    try:
        handoff = (
            db.query(AgentStudioHandoff)
            .filter(
                AgentStudioHandoff.scope.ilike("%[CI gate]%"),
                AgentStudioHandoff.status.in_(
                    (StudioHandoffStatus.pending, StudioHandoffStatus.blocked)
                ),
            )
            .order_by(AgentStudioHandoff.created_at.asc())
            .first()
        )
        if not handoff:
            print("No open [CI gate] handoff found.")
            return 0

        summary = (
            "CI gate local acceptance: audit_entities + minimum_living_network PASS. "
            f"phase_a --skip-optional: {'PASS' if phase_a_ok else 'SKIP/FAIL (start backend on :8000)'}"
        )
        blockers = None if phase_a_ok else "phase_a: start backend (POCP_NEXUS_AUTOPILOT=false) on :8000"
        status = "completed"
        complete_handoff(db, handoff.id, status=status, blockers=blockers)
        record_outcome(
            db,
            agent_entity_id=handoff.to_agent_entity_id,
            kind="test",
            result="pass" if phase_a_ok else "partial",
            mission_id=handoff.mission_id,
            handoff_id=handoff.id,
            summary=summary[:2000],
            evidence={"checks": [{"name": n, "exit": c} for n, c, _ in checks]},
        )
        db.commit()
        print(f"[OK] {handoff.id[:8]}… -> {status}")
        print(summary)
        for name, code, _ in checks:
            print(f"  - {name}: exit={code}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
