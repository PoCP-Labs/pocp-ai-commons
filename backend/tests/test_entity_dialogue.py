"""Tests for Entity Dialogue Protocol (pocp.entity_dialogue.v0.1)."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import LUMEN_0_ID
from models.contribution import AiVerifierResult, ContributionEvent, ContributionStatus
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStep, InvocationTrace
from models.task import Task, TaskStatus
from models.skill import Skill
from models.wallet import Wallet
from services.capability_import import import_skill_from_skill_md
from services.entity_dialogue import (
    ENTITY_DIALOGUE_SCHEMA,
    dialogue_manifest,
    route_dialogue,
    validate_dialogue_envelope,
)
from services.entity_register import register_entity


class EntityDialogueTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.human = Entity(
            entity_type=EntityType.human,
            name="Alice",
            status=EntityStatus.active,
        )
        self.db.add(self.human)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_dialogue_manifest_has_kinds(self):
        manifest = dialogue_manifest()
        self.assertEqual(manifest["schema"], ENTITY_DIALOGUE_SCHEMA)
        self.assertIn("invoke", manifest["kinds"])
        self.assertIn("federation_offer", manifest["kinds"])
        self.assertEqual(manifest["transport"]["physical_network"], "none")

    def test_validate_envelope_rejects_bad_schema(self):
        result = validate_dialogue_envelope({"schema": "wrong", "kind": "ping"})
        self.assertFalse(result["ok"])
        self.assertTrue(any("schema" in e for e in result["errors"]))

    def test_ping_dialogue(self):
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_ping_1",
            "kind": "ping",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["pong"])

    def test_discover_skill_entity(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="R-Tutor",
            description="Tutor skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_disc_1",
            "kind": "discover",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["result"]["entity"]["entity_id"], skill.id)
        self.assertIn("dialogue", response["bindings"])

    def test_invoke_records_invocation_step(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Invoke Skill",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_inv_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
            "payload": {"input": {"topic": "PoCP"}},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertFalse(response["result"].get("executed"))
        trace_id = response["refs"]["invocation_trace_id"]
        self.assertIsNotNone(trace_id)

        trace = self.db.query(InvocationTrace).filter(InvocationTrace.id == trace_id).first()
        self.assertIsNotNone(trace)
        steps = self.db.query(InvocationStep).filter(InvocationStep.trace_id == trace_id).all()
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].action, "uses")
        self.assertEqual(steps[0].source_entity_id, self.human.id)
        self.assertEqual(steps[0].target_entity_id, skill.id)

    def test_invoke_rejects_invalid_edge(self):
        agent = register_entity(
            self.db,
            entity_type="agent",
            name="Study Agent",
            description="Agent",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_bad_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": agent.id, "node_id": "test-node"},
            "payload": {"action": "calls"},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "rejected")

    def test_invoke_with_execute_runs_skill(self):
        llm = Entity(
            id=LUMEN_0_ID,
            entity_type=EntityType.llm,
            name="Lumen-0",
            status=EntityStatus.active,
        )
        self.db.add(llm)
        self.db.add(Wallet(entity_id=self.human.id, ai_credits=100, cp_balance=0))
        self.db.flush()
        skill_md = """---
name: dlg-exec
description: Dialogue execute test.
---
# Test
Answer briefly.
"""
        imported = import_skill_from_skill_md(
            self.db,
            source="pocp_native",
            skill_md=skill_md,
            maintainer_id=self.human.id,
            activate=True,
        )
        skill_id = imported["entity_id"]
        skill_entity = self.db.get(Entity, skill_id)
        skill_entity.name = "dlg-exec"
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_exec_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill_id, "node_id": "test-node"},
            "payload": {
                "execute": True,
                "input": "What is PoCP?",
                "llm_provider": "mock",
            },
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"].get("executed"))
        trace_id = response["refs"]["invocation_trace_id"]
        self.assertIn("capability_receipt_hashes", response["refs"])
        self.assertTrue(response["refs"]["capability_receipt_hashes"])
        self.assertIn("capability_receipts", response["result"])
        self.assertTrue(response["result"]["capability_receipts"])
        self.assertEqual(
            response["result"]["capability_receipts"][0]["schema"],
            "pocp.capability_receipt.v0.1",
        )
        steps = self.db.query(InvocationStep).filter(InvocationStep.trace_id == trace_id).all()
        self.assertGreater(len(steps), 1)
        self.assertEqual(steps[0].metadata_.get("dialogue_id"), "dlg_exec_1")
        self.assertIn("capability_receipt", steps[0].metadata_)

    def test_quote_capability_invoke(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Quote Skill",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        from models.wallet import Wallet

        self.db.add(Wallet(entity_id=self.human.id, ai_credits=50, cp_balance=0))
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_quote_1",
            "kind": "quote",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
            "payload": {"quote_action": "capability_invoke"},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["quote"]["allowed"])
        self.assertIn("exchange_id", response["refs"])
        self.assertEqual(response["result"]["exchange_kind"], "hybrid")

    def test_quote_rejects_non_human(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Skill2",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_quote_bad",
            "kind": "quote",
            "from": {"entity_id": skill.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "rejected")

    def test_finalize_notice_verdict(self):
        task = Task(title="Finalize task", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()
        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=self.human.id,
            contribution_type="knowledge",
            status=ContributionStatus.ai_verified,
        )
        self.db.add(contrib)
        self.db.flush()
        consensus = {
            "passed": True,
            "avg_score": 0.85,
            "avg_risk": 0.15,
            "suggested_cp": 30,
            "disagreement_high": False,
            "provider_results": [{"provider": "mock", "quality": 0.85, "risk_score": 0.15}],
        }
        self.db.add(
            AiVerifierResult(
                contribution_id=contrib.id,
                model_provider="multi_consensus",
                score=0.85,
                feedback=json.dumps(consensus),
                passed=True,
            )
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_fin_1",
            "kind": "finalize_notice",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
            "refs": {"contribution_id": contrib.id},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["can_finalize"])
        self.assertIn("verdict", response["result"])
        self.assertEqual(response["bindings"]["finalize"], f"/api/v1/contributions/{contrib.id}/finalize")

    def test_finalize_notice_apply_manual(self):
        task = Task(title="Finalize apply", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()
        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=self.human.id,
            contribution_type="knowledge",
            status=ContributionStatus.ai_verified,
        )
        self.db.add(contrib)
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_fin_apply",
            "kind": "finalize_notice",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
            "refs": {"contribution_id": contrib.id},
            "payload": {"apply_finalize": True, "use_auto_policy": False},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["finalization"]["applied"])
        self.db.refresh(contrib)
        self.assertEqual(contrib.status, ContributionStatus.approved)

    def test_submit_dialogue_creates_contribution(self):
        task = Task(title="Dialogue submit", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_sub_1",
            "kind": "submit",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
            "payload": {
                "task_id": task.id,
                "contribution_type": "knowledge",
                "description": "Via dialogue",
                "evidence": {"summary": "PoCP protocol submit test"},
            },
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["result"]["mode"], "submit")
        contrib_id = response["refs"]["contribution_id"]
        contrib = self.db.get(ContributionEvent, contrib_id)
        self.assertEqual(contrib.status, ContributionStatus.submitted)

    @patch("intelligence.capability_layer.verify_contribution", new_callable=AsyncMock)
    def test_attest_run_verify(self, mock_verify):
        mock_verify.return_value = {
            "passed": True,
            "avg_score": 0.9,
            "finalization": {"applied": False},
        }
        task = Task(title="Attest task", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()
        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=self.human.id,
            contribution_type="knowledge",
            status=ContributionStatus.submitted,
        )
        self.db.add(contrib)
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_att_1",
            "kind": "attest",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
            "refs": {"contribution_id": contrib.id},
            "payload": {"run_verify": True},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["result"]["mode"], "attest_verify")
        mock_verify.assert_awaited_once()

    def test_entity_target_mismatch_rejected(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Target Skill",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_mismatch",
            "kind": "discover",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
        }
        response = asyncio.run(
            route_dialogue(
                self.db,
                envelope,
                expected_target_entity_id="wrong-entity-id",
            )
        )
        self.assertEqual(response["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
