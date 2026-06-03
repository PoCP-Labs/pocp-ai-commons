"""Tests for federated MCP peer routing."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet
from services.mcp_import import import_mcp_server
from services.mcp_invoke import invoke_mcp_tool
from services.peer_mcp import _normalize_remote_invoke_mode, invoke_mcp_on_peer, peer_mcp_enabled
from services.remote_mcp_invoke import find_mcp_tool_by_portable_id, run_remote_mcp_invoke


class PeerMcpTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.human = Entity(entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.db.add(self.human)
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
        self.tool_entity_id = imported["tools"][0]["entity_id"]
        self.db.commit()
        tool = self.db.get(Entity, self.tool_entity_id)
        self.portable_id = (tool.metadata_ or {}).get("portable_id")

    def tearDown(self):
        self.db.close()
        os.environ.pop("ENABLE_PEER_MCP", None)
        os.environ.pop("ENABLE_PEER_COMPUTE", None)

    def test_find_mcp_tool_by_portable_id(self):
        found = find_mcp_tool_by_portable_id(self.db, self.portable_id)
        self.assertIsNotNone(found)
        entity, meta = found
        self.assertEqual(meta.get("mcp_tool_name"), "fetch")
        self.assertEqual(entity.id, self.tool_entity_id)

    def test_remote_mcp_invoke_stub(self):
        result = asyncio.run(
            run_remote_mcp_invoke(
                self.db,
                portable_id=self.portable_id,
                arguments={"url": "https://example.com"},
                invoke_mode="stub",
            )
        )
        self.assertEqual(result["invoke_mode"], "stub")
        self.assertIn("content", result["output"])

    @patch.dict(os.environ, {"ENABLE_PEER_MCP": "true"}, clear=False)
    def test_peer_mcp_enabled_flag(self):
        self.assertTrue(peer_mcp_enabled())

    def test_normalize_remote_invoke_mode_peer_to_stub(self):
        self.assertEqual(_normalize_remote_invoke_mode("peer"), "stub")

    def test_invoke_mcp_on_peer_parses_response(self):
        peer = MagicMock(node_id="node-b", base_url="http://127.0.0.1:8101")

        async def _run():
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "node_id": "node-b",
                "portable_id": self.portable_id,
                "invoke_mode": "stub",
                "output": {"content": [{"type": "text", "text": "peer ok"}], "isError": False},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            with patch("services.peer_mcp.httpx.AsyncClient", return_value=mock_client):
                return await invoke_mcp_on_peer(
                    peer,
                    portable_id=self.portable_id,
                    arguments={"url": "https://example.com"},
                    invoke_mode="stub",
                )

        result = asyncio.run(_run())
        self.assertEqual(result["peer_node_id"], "node-b")
        self.assertEqual(result["output"]["content"][0]["text"], "peer ok")

    @patch.dict(os.environ, {"ENABLE_PEER_MCP": "true"}, clear=False)
    def test_user_invoke_peer_mode(self):
        async def _run():
            with patch(
                "services.mcp_invoke.try_peer_mcp_invoke",
                AsyncMock(
                    return_value=(
                        {"content": [{"type": "text", "text": "from peer"}], "isError": False},
                        "node-b",
                    )
                ),
            ):
                return await invoke_mcp_tool(
                    self.db,
                    human_entity_id=self.human.id,
                    tool_entity_id=self.tool_entity_id,
                    arguments={"url": "https://example.com"},
                    force_mode="peer",
                )

        result = asyncio.run(_run())
        self.assertEqual(result["invoke_mode"], "peer")
        self.assertEqual(result["peer_node_id"], "node-b")


if __name__ == "__main__":
    unittest.main()
