"""PA-6 / CIP-P3.2 — MCP invoke security baseline tests."""

import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationTrace
from models.wallet import Wallet
from services.anti_abuse import (
    DAILY_MCP_INVOKE_LIMIT,
    HOURLY_MCP_INVOKE_LIMIT,
    check_mcp_invoke_rate_limit,
    enforce_mcp_invoke_auth_scope,
    enforce_mcp_invoke_baseline,
)
from services.mcp_import import import_mcp_server
from services.mcp_invoke import invoke_mcp_tool


class McpSecurityBaselineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.other = Entity(entity_type=EntityType.human, name="Bob", status=EntityStatus.active)
        self.agent = Entity(entity_type=EntityType.agent, name="Helper", status=EntityStatus.active)
        self.db.add_all([self.human, self.other, self.agent])
        self.db.flush()
        self.db.add_all(
            [
                Wallet(entity_id=self.human.id, ai_credits=100, cp_balance=0),
                Wallet(entity_id=self.other.id, ai_credits=100, cp_balance=0),
            ]
        )
        self.db.commit()

        imported = import_mcp_server(
            self.db,
            external_id="demo-fetch",
            name="Fetch MCP",
            description="Demo",
            maintainer_id=self.human.id,
            transport={"command": "npx", "args": ["-y", "pkg"]},
            tools=[{"name": "fetch", "description": "GET url"}],
            activate=True,
        )
        self.tool_entity_id = imported["tools"][0]["entity_id"]
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_auth_scope_rejects_initiator_mismatch(self):
        with self.assertRaises(HTTPException) as ctx:
            enforce_mcp_invoke_auth_scope(
                self.db,
                authenticated_entity_id=self.other.id,
                human_entity_id=self.human.id,
                agent_entity_id=None,
                tool_entity_id=self.tool_entity_id,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_auth_scope_rejects_disallowed_agent(self):
        self.human.metadata_ = {"mcp_allowed_agent_ids": []}
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            enforce_mcp_invoke_auth_scope(
                self.db,
                authenticated_entity_id=self.human.id,
                human_entity_id=self.human.id,
                agent_entity_id=self.agent.id,
                tool_entity_id=self.tool_entity_id,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_auth_scope_rejects_tool_without_capability_scope(self):
        tool = self.db.get(Entity, self.tool_entity_id)
        tool.metadata_ = {**(tool.metadata_ or {}), "auth_scopes": ["other_capability"]}
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            enforce_mcp_invoke_auth_scope(
                self.db,
                authenticated_entity_id=self.human.id,
                human_entity_id=self.human.id,
                agent_entity_id=None,
                tool_entity_id=self.tool_entity_id,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("services.anti_abuse.HOURLY_MCP_INVOKE_LIMIT", 1)
    def test_hourly_rate_limit(self):
        trace = InvocationTrace(
            initiator_id=self.human.id,
            model_provider="mcp-stub",
        )
        self.db.add(trace)
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            check_mcp_invoke_rate_limit(self.db, self.human.id)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Hourly", str(ctx.exception.detail))

    @patch("services.anti_abuse.DAILY_MCP_INVOKE_LIMIT", 0)
    def test_daily_rate_limit(self):
        with self.assertRaises(HTTPException) as ctx:
            check_mcp_invoke_rate_limit(self.db, self.human.id)
        self.assertEqual(ctx.exception.status_code, 429)

    def test_invoke_includes_security_audit(self):
        result = asyncio.run(
            invoke_mcp_tool(
                self.db,
                human_entity_id=self.human.id,
                tool_entity_id=self.tool_entity_id,
                arguments={"url": "https://example.com"},
            )
        )
        audit = result.get("security_audit") or {}
        self.assertEqual(audit.get("audit_kind"), "mcp_invoke")
        self.assertEqual(audit.get("trace_id"), result["trace_id"])
        self.assertEqual(audit.get("capability"), "mcp_tool_call")

    def test_baseline_constants_sane(self):
        self.assertGreater(HOURLY_MCP_INVOKE_LIMIT, 0)
        self.assertGreater(DAILY_MCP_INVOKE_LIMIT, HOURLY_MCP_INVOKE_LIMIT)

    def test_enforce_baseline_composes_scope_and_rate(self):
        enforce_mcp_invoke_baseline(
            self.db,
            authenticated_entity_id=self.human.id,
            human_entity_id=self.human.id,
            agent_entity_id=None,
            tool_entity_id=self.tool_entity_id,
        )


class StagingReceiptPolicyTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"POCP_REQUIRE_RECEIPT_SIGNATURE": "true", "POCP_SIGN_COMPUTE_RECEIPTS": "true"},
        clear=False,
    )
    def test_staging_receipt_policy_ok(self):
        from services.crypto_suite import validate_staging_receipt_policy

        report = validate_staging_receipt_policy()
        self.assertTrue(report["policy_ok"])

    @patch.dict(
        os.environ,
        {"POCP_REQUIRE_RECEIPT_SIGNATURE": "true", "POCP_SIGN_COMPUTE_RECEIPTS": "false"},
        clear=False,
    )
    def test_staging_receipt_policy_warns_when_unsigned(self):
        from services.crypto_suite import validate_staging_receipt_policy

        report = validate_staging_receipt_policy()
        self.assertFalse(report["policy_ok"])

    @patch.dict(os.environ, {"POCP_REQUIRE_RECEIPT_SIGNATURE": "true"}, clear=False)
    def test_settlement_rejects_unsigned_receipt(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from database import Base
        from models.entity import Entity, EntityStatus, EntityType
        from models.wallet import CreditTransaction, CreditType, Wallet
        from services.compute_receipt import build_compute_receipt
        from services.compute_settlement import settle_bilateral

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        db.add_all(
            [
                Entity(
                    id="human-1",
                    entity_type=EntityType.human,
                    name="Consumer",
                    status=EntityStatus.active,
                ),
                Entity(
                    id="llm-1",
                    entity_type=EntityType.llm,
                    name="Provider",
                    status=EntityStatus.active,
                ),
            ]
        )
        consumer = Wallet(entity_id="human-1", cp_balance=0, ai_credits=100)
        db.add(consumer)
        db.flush()
        db.add(
            CreditTransaction(
                wallet_id=consumer.id,
                amount=100,
                credit_type=CreditType.ai_credits,
                reason="grant",
            )
        )
        db.commit()
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
        )
        result = settle_bilateral(db, receipt, consumer_entity_id="human-1")
        self.assertFalse(result.get("settled"))
        self.assertEqual(result.get("reason"), "unsigned_or_invalid_receipt_signature")
        db.close()


if __name__ == "__main__":
    unittest.main()
