"""Live adapter configuration tests."""

import os
import unittest

from services.compute_adapters.live_config import (
    adapter_live_configured,
    adapter_live_enabled,
    adapter_runtime_status,
    effective_adapter_mode,
)
from services.compute_adapters.service import list_adapter_catalog


class ComputeAdapterLiveConfigTests(unittest.TestCase):
    def test_stub_mode_by_default(self):
        self.assertFalse(adapter_live_configured("akash"))
        self.assertEqual(effective_adapter_mode("akash"), "stub")

    def test_live_configured_when_env_set(self):
        with self._env("POCP_AKASH_API_URL", "https://akash.example/api"):
            self.assertTrue(adapter_live_configured("akash"))
            self.assertFalse(adapter_live_enabled("akash"))
            status = adapter_runtime_status("akash")
            self.assertTrue(status["live_configured"])
            self.assertFalse(status["live_wire_active"])
            self.assertEqual(status["mode"], "stub")

    def test_live_active_when_master_switch_on(self):
        with self._env("POCP_AKASH_API_URL", "https://akash.example/api"), self._env(
            "POCP_ADAPTER_LIVE_ENABLED", "true"
        ):
            self.assertTrue(adapter_live_enabled("akash"))
            status = adapter_runtime_status("akash")
            self.assertTrue(status["live_wire_active"])
            self.assertEqual(status["mode"], "live")

    def test_catalog_includes_runtime_status(self):
        catalog = list_adapter_catalog()
        akash = next(a for a in catalog["adapters"] if a["slug"] == "akash")
        self.assertIn("live_configured", akash)
        self.assertIn("note", akash)
        self.assertEqual(catalog.get("live_wire_doc"), "docs/COMPUTE-ADAPTER-LIVE-WIRE.md")

    def _env(self, key: str, value: str):
        return _EnvContext(key, value)


class _EnvContext:
    def __init__(self, key: str, value: str):
        self.key = key
        self.new_value = value
        self.old = os.environ.get(key)

    def __enter__(self):
        os.environ[self.key] = self.new_value
        return self

    def __exit__(self, *args):
        if self.old is None:
            os.environ.pop(self.key, None)
        else:
            os.environ[self.key] = self.old


if __name__ == "__main__":
    unittest.main()
