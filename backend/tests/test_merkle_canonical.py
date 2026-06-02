"""Unified Merkle tree — ledger and ProtocolEvent overlay compatibility."""

import unittest

from services.ledger_merkle import merkle_root as ledger_merkle_root
from services.merkle_canonical import (
    MERKLE_ALGORITHM,
    build_inclusion_bundle_unified,
    merkle_root_unified,
    merkle_root_unified_display,
    normalize_merkle_leaf,
    verify_merkle_inclusion_unified,
)
from services.network.merkle import MerkleService
from services.network.proof_overlay import build_protocol_event_overlay_block
from services.network.types import canonical_hash


class MerkleCanonicalTests(unittest.TestCase):
    def test_normalize_strips_prefix(self):
        bare = "a" * 64
        self.assertEqual(normalize_merkle_leaf(f"sha256:{bare}"), bare)

    def test_unified_root_matches_ledger_on_normalized_leaves(self):
        leaves = [canonical_hash({"i": i}) for i in range(4)]
        unified = merkle_root_unified(leaves)
        ledger_style = ledger_merkle_root([normalize_merkle_leaf(h) for h in leaves])
        self.assertEqual(unified, ledger_style)

    def test_network_merkle_service_hex_matches_unified(self):
        leaves = [canonical_hash({"x": 1}), canonical_hash({"x": 2})]
        svc = MerkleService()
        self.assertEqual(svc.merkle_root_hex(leaves), merkle_root_unified(leaves))
        self.assertTrue(svc.merkle_root(leaves).startswith("sha256:"))

    def test_inclusion_bundle_roundtrip(self):
        leaves = [canonical_hash({"n": i}) for i in range(3)]
        target = leaves[1]
        bundle = build_inclusion_bundle_unified(leaves, target)
        assert bundle is not None
        self.assertEqual(bundle["algorithm"], MERKLE_ALGORITHM)
        self.assertTrue(
            verify_merkle_inclusion_unified(
                target,
                bundle["merkle_proof"],
                bundle["merkle_root"],
            )
        )

    def test_proof_overlay_block_from_mock_trace(self):
        step = type(
            "S",
            (),
            {
                "step_order": 1,
                "source_entity_id": "h1",
                "target_entity_id": "s1",
                "action": "uses",
                "metadata_": {"dialogue_id": "dlg_1", "dialogue_kind": "invoke"},
            },
        )()
        trace = type("T", (), {"id": "tr1", "steps": [step]})()
        block = build_protocol_event_overlay_block([trace])
        self.assertIsNotNone(block)
        assert block is not None
        self.assertEqual(block["merkle_algorithm"], MERKLE_ALGORITHM)
        self.assertEqual(block["leaf_count"], 1)
        self.assertEqual(len(block["inclusions"]), 1)


if __name__ == "__main__":
    unittest.main()
