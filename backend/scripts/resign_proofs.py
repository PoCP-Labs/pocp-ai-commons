#!/usr/bin/env python3
"""Re-export contribution proofs under the active crypto suite (hybrid re-sign campaign).

Usage:
  python backend/scripts/resign_proofs.py --out-dir proofs/resigned
  python backend/scripts/resign_proofs.py --verify --limit 10
  POCP_CRYPTO_SUITE=pocp-crypto-v0.2-hybrid python backend/scripts/resign_proofs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal, init_db
from models.contribution import ContributionEvent, ContributionStatus
from services.crypto_suite import active_crypto_suite, crypto_readiness_report
from services.proof import build_contribution_proof_packet
from services.verify_standalone import verify_proof_integrity


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-sign approved contribution proofs")
    parser.add_argument("--out-dir", type=Path, default=None, help="Write JSON proofs to directory")
    parser.add_argument("--verify", action="store_true", help="Run offline verify on each proof")
    parser.add_argument("--limit", type=int, default=0, help="Max contributions (0 = all)")
    parser.add_argument("--status", default="approved", help="Contribution status filter")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        query = (
            db.query(ContributionEvent)
            .filter(ContributionEvent.status == ContributionStatus(args.status))
            .order_by(ContributionEvent.created_at.asc())
        )
        if args.limit > 0:
            query = query.limit(args.limit)
        contributions = query.all()

        if args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)

        report = crypto_readiness_report()
        print(f"Active suite: {report['active_crypto_suite']}")
        print(f"Hybrid enabled: {report['hybrid_signing_enabled']}")
        print(f"PQC: {report['pqc_implementation']}")
        print(f"Contributions to re-sign: {len(contributions)}")

        summary = {
            "resigned_at": datetime.now(timezone.utc).isoformat(),
            "crypto_suite": active_crypto_suite(),
            "count": 0,
            "verified": 0,
            "failed": 0,
            "items": [],
        }

        for contrib in contributions:
            packet = build_contribution_proof_packet(db, contrib.id)
            if not packet:
                summary["failed"] += 1
                summary["items"].append({"contribution_id": contrib.id, "error": "proof_build_failed"})
                continue

            item = {
                "contribution_id": contrib.id,
                "proof_id": packet.get("proof_id"),
                "proof_hash": (packet.get("integrity") or {}).get("proof_hash"),
                "crypto_suite": (packet.get("integrity") or {}).get("crypto_suite"),
                "has_pqc": "pqc" in ((packet.get("federation") or {}).get("signatures") or {}),
            }

            if args.verify:
                result = verify_proof_integrity(packet)
                item["verify_valid"] = result.get("valid")
                item["verify_checks"] = [c.get("check") for c in result.get("checks", []) if not c.get("valid")]
                if result.get("valid"):
                    summary["verified"] += 1
                else:
                    summary["failed"] += 1

            if args.out_dir:
                out_path = args.out_dir / f"pocp-proof-{contrib.id}.json"
                out_path.write_text(json.dumps(packet, indent=2, default=str), encoding="utf-8")
                item["path"] = str(out_path)

            summary["count"] += 1
            summary["items"].append(item)
            print(
                f"  ✓ {contrib.id[:8]}… suite={item.get('crypto_suite')} "
                f"pqc={item.get('has_pqc')} hash={str(item.get('proof_hash', ''))[:12]}…"
            )

        if args.out_dir:
            manifest = args.out_dir / "resign_manifest.json"
            manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"Manifest: {manifest}")

        print(f"Done: {summary['count']} proofs, verified={summary['verified']}, failed={summary['failed']}")
        return 0 if summary["failed"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
