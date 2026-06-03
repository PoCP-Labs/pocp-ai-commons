"""Regression: BACKEND_URL / compose host port alignment (api: timed out in super-loop)."""

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
_COMPOSE = _REPO / "docker-compose.yml"
_ENV_EXAMPLE = _REPO / "backend" / ".env.example"
_SMOKE_WORKFLOW = _REPO / ".github" / "workflows" / "smoke-test.yml"
_FED_WORKFLOW = _REPO / ".github" / "workflows" / "phase-a-federation.yml"


class EnvBackendUrlAlignmentTests(unittest.TestCase):
    def test_compose_maps_host_8008_to_container_8000(self):
        text = _COMPOSE.read_text(encoding="utf-8")
        self.assertRegex(text, r'["\']8008:8000["\']')

    def test_env_example_documents_docker_backend_url_8008(self):
        text = _ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn("8008", text, "Document docker host port in backend/.env.example")

    def test_platform_health_default_matches_compose_host_port(self):
        import os

        from services.agent_studio.platform_health import probe_api_health

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("httpx.get") as mock_get:
                mock_resp = mock.MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "service": "pocp-ai-commons",
                    "database": {"status": "ok"},
                }
                mock_get.return_value = mock_resp
                result = probe_api_health()
        self.assertEqual(result["base"], "http://127.0.0.1:8008")

    def test_run_phase_a_default_matches_compose_host_port(self):
        script = _REPO / "backend" / "scripts" / "run_phase_a_acceptance.py"
        spec = importlib.util.spec_from_file_location("run_phase_a_acceptance", script)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        self.assertEqual(mod.DEFAULT_BASE, "http://127.0.0.1:8008")

    def test_run_phase_a_wrapper_scripts_export_backend_url(self):
        for name in ("run-phase-a.ps1", "run-phase-a.sh"):
            text = (_REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("BACKEND_URL", text, f"{name} must set BACKEND_URL for super-loop probes")

    def test_smoke_test_workflow_exports_backend_url_for_ci_api(self):
        text = _SMOKE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("BACKEND_URL", text)
        self.assertRegex(text, r"BACKEND_URL:\s*http://127\.0\.0\.1:8765")

    def test_federation_workflow_exports_backend_url_for_node_a(self):
        text = _FED_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("BACKEND_URL", text)
        self.assertRegex(text, r"BACKEND_URL:\s*http://127\.0\.0\.1:8100")

    def test_run_phase_a_syncs_backend_url_env_helper(self):
        script = _REPO / "backend" / "scripts" / "run_phase_a_acceptance.py"
        text = script.read_text(encoding="utf-8")
        self.assertIn("def sync_backend_url_env", text)
        self.assertIn('os.environ["BACKEND_URL"]', text)
        self.assertIn("sync_backend_url_env(base)", text)


if __name__ == "__main__":
    unittest.main()
