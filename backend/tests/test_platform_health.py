"""Regression tests for Nexus platform health probes (api timeout / port alignment)."""

import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.agent_studio.platform_health import (
    probe_api_health,
    probe_database,
    probe_platform,
)


class PlatformHealthTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_probe_database_ok(self):
        result = probe_database(self.db)
        self.assertTrue(result["ok"])
        self.assertIn("postgres ping ok", result["detail"])

    @patch.dict(os.environ, {"BACKEND_URL": "http://127.0.0.1:8008"}, clear=False)
    @patch("httpx.get")
    def test_probe_api_health_ok(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "service": "pocp-ai-commons",
            "status": "ok",
            "database": {"status": "ok"},
            "version": "0.4.0",
        }
        mock_get.return_value = mock_resp

        result = probe_api_health()
        self.assertTrue(result["ok"])
        self.assertEqual(result["base"], "http://127.0.0.1:8008")
        mock_get.assert_called_once_with("http://127.0.0.1:8008/health", timeout=10.0)

    @patch.dict(os.environ, {"BACKEND_URL": "http://127.0.0.1:8008"}, clear=False)
    @patch("httpx.get")
    def test_probe_api_health_timeout_surfaces_detail(self, mock_get):
        import httpx

        mock_get.side_effect = httpx.ReadTimeout("timed out")

        result = probe_api_health()
        self.assertFalse(result["ok"])
        self.assertIn("timed out", result["detail"])

    @patch.dict(os.environ, {"BACKEND_URL": "http://127.0.0.1:8008"}, clear=False)
    @patch("services.agent_studio.platform_health.probe_api_health")
    def test_probe_platform_aggregates_api_timeout_issue(self, mock_api):
        mock_api.return_value = {"ok": False, "detail": "timed out", "base": "http://127.0.0.1:8008"}

        result = probe_platform(self.db)
        self.assertFalse(result["ok"])
        self.assertIn("api: timed out", result["issues"])
        self.assertTrue(result["database"]["ok"])

    @patch.dict(os.environ, {}, clear=True)
    @patch("httpx.get")
    def test_probe_api_health_default_port_8008(self, mock_get):
        """Docker maps host :8008 → container :8000; default probe must match compose."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"service": "pocp-ai-commons", "database": {"status": "ok"}}
        mock_get.return_value = mock_resp

        result = probe_api_health()
        self.assertTrue(result["ok"])
        self.assertEqual(result["base"], "http://127.0.0.1:8008")
        mock_get.assert_called_once_with("http://127.0.0.1:8008/health", timeout=10.0)


if __name__ == "__main__":
    unittest.main()
