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


if __name__ == "__main__":
    unittest.main()
