"""Tests for protocol-layer rights conversion and capability receipts."""

import unittest
from unittest.mock import MagicMock

from models.contribution import ParticipantRole
from models.entity import EntityType
from services.capability_receipt import (
    CAPABILITY_RECEIPT_SCHEMA,
    build_capability_receipt,
    compute_capability_receipt_hash,
    infer_capability_kind,
)
from services.rights_conversion import (
    CONVERSION_SCHEMA,
    RIGHTS_RULES_SCHEMA,
    build_contribution_to_rights_conversion,
    plan_participant_allocation,
    rights_rules_manifest,
)


class RightsConversionTests(unittest.TestCase):
    def test_rights_rules_manifest_shape(self):
        manifest = rights_rules_manifest()
        self.assertEqual(manifest["schema"], RIGHTS_RULES_SCHEMA)
        self.assertIn("bc", manifest["rights"])
        self.assertIn("cp", manifest["rights"])
        self.assertFalse(manifest["portability"]["cp_transferable"])

    def test_human_creator_plan_includes_cp_and_bc(self):
        participant = MagicMock(
            entity_id="human-1",
            role=ParticipantRole.creator,
            weight=0.4,
        )
        entity = MagicMock(id="human-1", entity_type=EntityType.human, name="Rain")
        plan = plan_participant_allocation(participant, entity)
        kinds = {g["kind"] for g in plan["grants"]}
        self.assertEqual(kinds, {"cp", "bc"})
        self.assertEqual(plan["grants"][0]["amount"], 20.0)

    def test_skill_provider_plan_reputation(self):
        participant = MagicMock(
            entity_id="skill-1",
            role=ParticipantRole.skill_provider,
            weight=0.15,
        )
        entity = MagicMock(id="skill-1", entity_type=EntityType.skill, name="R-Tutor")
        plan = plan_participant_allocation(participant, entity)
        kinds = {g["kind"] for g in plan["grants"]}
        self.assertIn("reputation", kinds)
        rep = next(g for g in plan["grants"] if g["kind"] == "reputation")
        self.assertEqual(rep["amount"], 5.0)

    def test_conversion_block_schema(self):
        contribution = MagicMock(
            id="c-1",
            status=MagicMock(value="approved"),
            participants=[],
        )
        block = build_contribution_to_rights_conversion(contribution, {}, applied_rewards={"credits": []})
        self.assertEqual(block["schema"], CONVERSION_SCHEMA)
        self.assertEqual(block["rules_schema"], RIGHTS_RULES_SCHEMA)
        self.assertEqual(block["applied_rewards"], {"credits": []})


class CapabilityReceiptTests(unittest.TestCase):
    def test_infer_kind_from_action(self):
        self.assertEqual(infer_capability_kind("invokes_llm"), "llm")
        self.assertEqual(infer_capability_kind("calls"), "skill")

    def test_receipt_hash_stable(self):
        step = MagicMock(
            step_order=1,
            source_entity_id="h1",
            target_entity_id="s1",
            action="calls",
            metadata_={"provider": "mock"},
        )
        receipt = build_capability_receipt(
            trace_id="t1",
            step=step,
            target_entity=MagicMock(entity_type=EntityType.skill, name="Skill-A", metadata_={}),
            request_summary="hello",
            response_summary="world",
        )
        self.assertEqual(receipt["schema"], CAPABILITY_RECEIPT_SCHEMA)
        self.assertIn("request_hash", receipt)
        self.assertIn("response_hash", receipt)
        expected = compute_capability_receipt_hash(receipt)
        self.assertEqual(receipt["receipt_hash"], expected)


if __name__ == "__main__":
    unittest.main()
