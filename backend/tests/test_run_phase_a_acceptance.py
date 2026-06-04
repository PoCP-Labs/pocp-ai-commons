"""Unit tests for Phase A acceptance HTTP steps (PA-5 entity catalog gate)."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_phase_a_acceptance.py"
_spec = importlib.util.spec_from_file_location("run_phase_a_acceptance", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["run_phase_a_acceptance"] = _mod
_spec.loader.exec_module(_mod)

step_entity_catalog_complete = _mod.step_entity_catalog_complete
step_health = _mod.step_health
step_conformance_well_known = _mod.step_conformance_well_known
step_conformance_pocp_capabilities = _mod.step_conformance_pocp_capabilities
step_conformance_pocp_invoke_ping = _mod.step_conformance_pocp_invoke_ping
sync_backend_url_env = _mod.sync_backend_url_env
DEFAULT_BASE = _mod.DEFAULT_BASE
ONTOLOGY_TYPE_COUNT = _mod.ONTOLOGY_TYPE_COUNT


def _ontology_types() -> list[str]:
    return [f"type_{i}" for i in range(ONTOLOGY_TYPE_COUNT)]


def _entities_for_types(types: list[str]) -> list[dict]:
    rows: list[dict] = []
    for t in types:
        rows.append({"id": f"ent-{t}", "entity_type": t, "name": t})
    for infra_id in _mod.INFRASTRUCTURE_ENTITY_IDS:
        rows.append({"id": infra_id, "entity_type": "compute_node", "name": infra_id})
    return rows


class PhaseAAcceptanceDefaultsTests(unittest.TestCase):
    def test_default_base_matches_docker_compose_host_port(self):
        """Phase A acceptance must target :8008 (compose maps host 8008 → container 8000)."""
        self.assertEqual(DEFAULT_BASE, "http://127.0.0.1:8008")

    @patch.object(
        _mod,
        "get_json",
        side_effect=URLError("timed out"),
    )
    def test_health_failure_hints_compose_port_on_8000(self, _mock_get):
        ok, detail = step_health("http://127.0.0.1:8000")
        self.assertFalse(ok)
        self.assertIn("8008", detail)

    def test_sync_backend_url_env_sets_probe_target(self):
        with patch.dict(os.environ, {}, clear=True):
            sync_backend_url_env("http://127.0.0.1:8008")
            self.assertEqual(os.environ["BACKEND_URL"], "http://127.0.0.1:8008")


class EntityCatalogAcceptanceStepTests(unittest.TestCase):
    @patch.object(_mod, "get_json")
    def test_passes_when_ontology_types_and_registry_complete(self, mock_get_json):
        types = _ontology_types()
        mock_get_json.side_effect = [
            {"entity_types": types, "spec_version": "0.3"},
            _entities_for_types(types),
            {"count": 12, "items": [{"capability_id": f"c{i}"} for i in range(12)]},
        ]
        ok, detail = step_entity_catalog_complete("http://127.0.0.1:8000")
        self.assertTrue(ok, detail)
        self.assertIn("capability_count", detail)

    @patch.object(_mod, "get_json")
    def test_fails_when_entity_type_missing(self, mock_get_json):
        types = _ontology_types()
        partial = types[:-1]
        mock_get_json.side_effect = [
            {"entity_types": types},
            _entities_for_types(partial),
            {"count": 12, "items": []},
        ]
        ok, detail = step_entity_catalog_complete("http://127.0.0.1:8000")
        self.assertFalse(ok)
        self.assertIn("missing_types", detail)

    @patch.object(_mod, "get_json")
    def test_fails_when_capability_registry_below_minimum(self, mock_get_json):
        types = _ontology_types()
        mock_get_json.side_effect = [
            {"entity_types": types},
            _entities_for_types(types),
            {"count": 0, "items": []},
        ]
        ok, detail = step_entity_catalog_complete("http://127.0.0.1:8000")
        self.assertFalse(ok)
        self.assertIn("capability_count", detail)


class ConformanceAcceptanceStepTests(unittest.TestCase):
    def _well_known_manifest(self) -> dict:
        return {
            "protocol": "pocp-node-manifest-v0.2-capability-first",
            "kind": "instance",
            "instance_id": "pocp-node-local",
            "display_name": "PoCP",
            "facets": ["instance_host"],
            "archive_entity_id": "pocp-org-ai-commons",
            "endpoints": {
                "well_known": "http://127.0.0.1:8000/.well-known/pocp-node.json",
                "health": "http://127.0.0.1:8000/health",
                "capabilities_directory": "http://127.0.0.1:8000/api/v1/capabilities/directory",
                "ledger_verify": "http://127.0.0.1:8000/api/v1/ledger/verify",
                "federation_node": "http://127.0.0.1:8000/api/v1/federation/node",
            },
            "updated_at": "2026-06-04T00:00:00+00:00",
        }

    @patch.object(_mod, "get_json")
    def test_conformance_well_known_passes(self, mock_get_json):
        mock_get_json.side_effect = [
            self._well_known_manifest(),
            {
                "endpoints": {
                    "pocp_health": "http://127.0.0.1:8000/pocp/health",
                    "pocp_capabilities": "http://127.0.0.1:8000/pocp/capabilities",
                    "pocp_invoke": "http://127.0.0.1:8000/pocp/invoke",
                    "pocp_node": "http://127.0.0.1:8000/pocp/node",
                }
            },
        ]
        ok, detail = step_conformance_well_known("http://127.0.0.1:8000")
        self.assertTrue(ok, detail)

    @patch.object(_mod, "get_json")
    def test_conformance_well_known_fails_missing_pocp_endpoints(self, mock_get_json):
        mock_get_json.side_effect = [
            self._well_known_manifest(),
            {"endpoints": {"pocp_health": "http://127.0.0.1:8000/pocp/health"}},
        ]
        ok, detail = step_conformance_well_known("http://127.0.0.1:8000")
        self.assertFalse(ok)
        self.assertIn("missing_pocp_endpoints", detail)

    @patch.object(_mod, "get_json")
    def test_conformance_pocp_capabilities_passes(self, mock_get_json):
        mock_get_json.return_value = {"items": [{"capability_id": "c1"}], "count": 1}
        ok, detail = step_conformance_pocp_capabilities("http://127.0.0.1:8000")
        self.assertTrue(ok, detail)
        self.assertIn("item_count", detail)

    @patch.object(_mod, "get_json")
    def test_conformance_pocp_capabilities_fails_without_items(self, mock_get_json):
        mock_get_json.return_value = {"count": 0}
        ok, detail = step_conformance_pocp_capabilities("http://127.0.0.1:8000")
        self.assertFalse(ok)
        self.assertIn("items", detail)

    @patch.object(_mod, "post_json")
    @patch.object(_mod, "get_json")
    def test_conformance_pocp_invoke_ping_passes(self, mock_get_json, mock_post_json):
        mock_get_json.side_effect = [
            self._well_known_manifest(),
            {"node_id": "node-local"},
        ]
        mock_post_json.return_value = {
            "status": "accepted",
            "result": {"pong": True},
        }
        ok, detail = step_conformance_pocp_invoke_ping("http://127.0.0.1:8000")
        self.assertTrue(ok, detail)
        self.assertEqual(mock_post_json.call_args[0][0], "http://127.0.0.1:8000/pocp/invoke")
        envelope = mock_post_json.call_args[0][1]
        self.assertEqual(envelope["kind"], "ping")
        self.assertEqual(envelope["schema"], "pocp.entity_dialogue.v0.1")


if __name__ == "__main__":
    unittest.main()
