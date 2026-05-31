"""Tests for pow.yaml interop export."""

import unittest
from unittest.mock import MagicMock, patch

from services.pow_export import (
    POW_INTEROP_SCHEMA,
    proof_packet_to_pow_record,
    validate_pow_record,
)


SAMPLE_PROOF = {
    "spec_version": "0.1",
    "proof_schema": "pocp.contribution_proof.v0.1",
    "contribution_event": {
        "id": "c-1",
        "contribution_type": "knowledge",
        "description": "Demo",
        "status": "approved",
        "created_at": "2026-01-01T00:00:00",
        "task": {"id": "t-1", "title": "Task"},
    },
    "entity_identity": {
        "primary": {"id": "h-1", "name": "Rain", "entity_type": "human"},
        "participants": [],
    },
    "evidence": {"content_hash": "abc123", "items": []},
    "verification": {"ai_advisory": [], "human_reviews": []},
    "finalization": {"mode": "manual", "policy_version": "0.1"},
    "contribution_to_rights_conversion": {
        "rules_schema": "pocp.rights_rules.v0.1",
        "rules_version": "0.1",
        "planned_allocations": [],
    },
    "invocation_trace": {"traces": [], "trace_count": 0},
    "integrity": {"proof_hash": "deadbeef", "evidence_hash": "abc123"},
}


class PowExportTests(unittest.TestCase):
    def test_proof_to_pow_record_shape(self):
        record = proof_packet_to_pow_record(SAMPLE_PROOF)
        self.assertEqual(record["schema"], POW_INTEROP_SCHEMA)
        self.assertEqual(record["contribution_id"], "c-1")
        self.assertEqual(record["contributor"]["entity_id"], "h-1")
        self.assertEqual(record["integrity"]["pocp_proof_schema"], "pocp.contribution_proof.v0.1")

    def test_validate_pow_record(self):
        record = proof_packet_to_pow_record(SAMPLE_PROOF)
        self.assertEqual(validate_pow_record(record), [])

    def test_build_pow_export_not_found(self):
        from services.pow_export import build_pow_export

        db = MagicMock()
        with patch("services.pow_export.build_contribution_proof_packet", return_value=None):
            result = build_pow_export(db, "missing")
        self.assertFalse(result["valid"])
        self.assertIsNone(result["pow_record"])


if __name__ == "__main__":
    unittest.main()
