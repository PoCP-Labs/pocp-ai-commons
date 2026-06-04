"""Tests for MCP tool stub invocation."""

import asyncio
import unittest

from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationTrace
from models.wallet import Wallet
from services.mcp_import import import_mcp_server
from services.mcp_invoke import invoke_mcp_tool


class McpInvokeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.agent = Entity(entity_type=EntityType.agent, name="Helper", status=EntityStatus.active)
        self.db.add_all([self.human, self.agent])
        self.db.flush()
        self.db.add(Wallet(entity_id=self.human.id, ai_credits=100, cp_balance=0))
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
        self.server_entity_id = imported["entity_id"]
        self.tool_entity_id = imported["tools"][0]["entity_id"]
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_invoke_mcp_tool_stub(self):
        result = asyncio.run(
            invoke_mcp_tool(
                self.db,
                human_entity_id=self.human.id,
                tool_entity_id=self.tool_entity_id,
                arguments={"url": "https://example.com"},
            )
        )
        self.assertEqual(result["execution_type"], "mcp_tool")
        self.assertEqual(result["invoke_mode"], "stub")
        self.assertEqual(result["mcp_tool_name"], "fetch")
        self.assertTrue(result["trace_id"])
        self.assertIn("content", result["output"])

        trace = self.db.get(InvocationTrace, result["trace_id"])
        self.assertIsNotNone(trace)
        self.assertEqual(trace.model_provider, "mcp-stub")
        actions = [s.action for s in trace.steps]
        self.assertEqual(actions, ["uses", "invokes_mcp"])
        invoke_step = [s for s in trace.steps if s.action == "invokes_mcp"][0]
        self.assertEqual((invoke_step.metadata_ or {}).get("mcp_spec_version"), "2024-11-05")
        self.assertEqual((invoke_step.metadata_ or {}).get("invoke_mode"), "stub")
        self.assertIn("capability_receipts", result)
        self.assertEqual(len(result["capability_receipts"]), 2)
        self.assertIn("request_hash", result["capability_receipts"][-1])
        self.assertIn("exchange_id", result)
        self.assertIn("billing", result)
        self.assertGreater(result["billing"]["credits_spent"], 0)
        self.assertEqual((result.get("security_audit") or {}).get("audit_kind"), "mcp_invoke")

    def test_invoke_requires_active_tool(self):
        tool = self.db.get(Entity, self.tool_entity_id)
        tool.status = EntityStatus.pending
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                invoke_mcp_tool(
                    self.db,
                    human_entity_id=self.human.id,
                    tool_entity_id=self.tool_entity_id,
                    arguments={},
                )
            )
        self.assertIn("active", str(ctx.exception.detail).lower())

    def test_invoke_with_agent_chain(self):
        result = asyncio.run(
            invoke_mcp_tool(
                self.db,
                human_entity_id=self.human.id,
                tool_entity_id=self.tool_entity_id,
                agent_entity_id=self.agent.id,
                arguments={"url": "https://pocp.example"},
            )
        )
        actions = [s["action"] for s in result["invocation_chain"]]
        self.assertEqual(actions, ["uses", "calls", "invokes_mcp"])

    def test_invoke_mock_output_runtime(self):
        tool = self.db.get(Entity, self.tool_entity_id)
        tool.metadata_ = {
            **(tool.metadata_ or {}),
            "runtime": {"mock_output": {"content": [{"type": "text", "text": "mocked"}], "isError": False}},
        }
        self.db.commit()

        result = asyncio.run(
            invoke_mcp_tool(
                self.db,
                human_entity_id=self.human.id,
                tool_entity_id=self.tool_entity_id,
                arguments={"url": "https://example.com"},
            )
        )
        self.assertEqual(result["output"]["content"][0]["text"], "mocked")

    def test_invoke_external_result(self):
        result = asyncio.run(
            invoke_mcp_tool(
                self.db,
                human_entity_id=self.human.id,
                tool_entity_id=self.tool_entity_id,
                arguments={"url": "https://example.com"},
                external_result={"text": "fetched externally", "isError": False},
            )
        )
        self.assertEqual(result["invoke_mode"], "external")
        self.assertEqual(result["output"]["content"][0]["text"], "fetched externally")

        trace = self.db.get(InvocationTrace, result["trace_id"])
        self.assertEqual(trace.model_provider, "mcp-external")

    def test_invoke_live_mode_mocked_wire(self):
        with patch(
            "services.mcp_invoke.wire_call_mcp_tool",
            AsyncMock(
                return_value={"content": [{"type": "text", "text": "live ok"}], "isError": False}
            ),
        ):
            result = asyncio.run(
                invoke_mcp_tool(
                    self.db,
                    human_entity_id=self.human.id,
                    tool_entity_id=self.tool_entity_id,
                    arguments={"url": "https://example.com"},
                    force_mode="live",
                )
            )
        self.assertEqual(result["invoke_mode"], "live")
        self.assertEqual(result["output"]["content"][0]["text"], "live ok")


if __name__ == "__main__":
    unittest.main()
