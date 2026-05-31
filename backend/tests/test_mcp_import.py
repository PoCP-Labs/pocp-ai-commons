"""Tests for MCP server/tool import."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.mcp_import import (
    import_mcp_server,
    list_mcp_catalog,
    parse_mcp_servers_config,
    sync_bundled_mcp_capabilities,
)


class McpImportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        org = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
        )
        human = Entity(
            entity_type=EntityType.human,
            name="Maintainer",
            status=EntityStatus.active,
        )
        self.db.add_all([org, human])
        self.db.commit()
        self.maintainer_id = human.id

    def tearDown(self):
        self.db.close()

    def test_parse_mcp_servers_config(self):
        rows = parse_mcp_servers_config(
            {
                "mcpServers": {
                    "time": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-time"],
                        "tools": [{"name": "get_current_time", "description": "tz"}],
                    }
                }
            }
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["external_id"], "time")
        self.assertEqual(rows[0]["transport"]["transport"], "stdio")

    def test_import_mcp_server_and_tools(self):
        result = import_mcp_server(
            self.db,
            external_id="demo-fetch",
            name="Fetch MCP",
            description="Demo",
            maintainer_id=self.maintainer_id,
            transport={"command": "npx", "args": ["-y", "pkg"]},
            tools=[{"name": "fetch", "description": "GET url"}],
            activate=False,
        )
        self.assertTrue(result["created"])
        self.assertEqual(result["tools_imported"], 1)
        catalog = list_mcp_catalog(self.db)
        self.assertEqual(len(catalog), 2)
        roles = {c["mcp_role"] for c in catalog}
        self.assertEqual(roles, {"server", "tool"})

    def test_sync_bundled_mcp(self):
        results = sync_bundled_mcp_capabilities(self.db, maintainer_id=self.maintainer_id)
        self.assertGreaterEqual(len(results), 2)
        catalog = list_mcp_catalog(self.db)
        self.assertGreaterEqual(len(catalog), 4)


if __name__ == "__main__":
    unittest.main()
