"""Bitcoin-inspired peer addrbook (score, ban, addr relay)."""

import os
import unittest

from services.federation_peer_addrbook import (
    default_addrbook,
    extract_known_peer_urls,
    get_peer_addrbook,
    is_peer_banned,
    is_peer_routable,
    record_probe_result,
)


class FederationPeerAddrbookTests(unittest.TestCase):
    def test_default_addrbook(self):
        book = default_addrbook()
        self.assertEqual(book["score"], 0.5)
        self.assertFalse(book["banned"])

    def test_success_increases_score(self):
        book = record_probe_result(None, success=True, ledger_valid=True)
        self.assertGreater(book["score"], 0.5)
        self.assertEqual(book["consecutive_failures"], 0)

    def test_failures_decrease_score(self):
        meta = {"peer_addrbook": default_addrbook()}
        book = record_probe_result(meta, success=False, error="timeout")
        self.assertLess(book["score"], 0.5)
        self.assertEqual(book["consecutive_failures"], 1)

    def test_ban_after_threshold(self):
        os.environ["POCP_PEER_SCORE_BAN_FAILURES"] = "3"
        meta = {"peer_addrbook": {**default_addrbook(), "consecutive_failures": 2}}
        book = record_probe_result(meta, success=False, error="down")
        self.assertTrue(book["banned"])
        self.assertTrue(is_peer_banned({"peer_addrbook": book}))
        self.assertFalse(is_peer_routable({"peer_addrbook": book}))

    def test_extract_known_peer_urls(self):
        manifest = {
            "known_peers": [
                {"node_id": "a", "base_url": "http://a:8008"},
                "http://b:8009",
            ],
            "discovery": {"known_peers": ["http://c:8010"]},
        }
        urls = extract_known_peer_urls(manifest)
        self.assertEqual(urls, ["http://a:8008", "http://b:8009", "http://c:8010"])

    def test_success_clears_probe_failure_ban(self):
        meta = {
            "peer_addrbook": {
                **default_addrbook(),
                "banned": True,
                "ban_reason": "probe_failures",
            }
        }
        book = record_probe_result(meta, success=True, ledger_valid=True)
        self.assertFalse(book["banned"])

    def test_fetch_bootstrap_peer_urls(self):
        from unittest.mock import patch

        from services.federation_peer_addrbook import fetch_bootstrap_peer_urls

        with patch.dict(os.environ, {"POCP_PEER_BOOTSTRAP_URL": "http://bootstrap/peers.json"}):
            with patch("services.federation_peers._get_json") as mock_get:
                mock_get.return_value = {
                    "known_peers": [
                        {"node_id": "x", "base_url": "http://x:8008"},
                        "http://y:8009",
                    ]
                }
                urls = fetch_bootstrap_peer_urls()
        self.assertEqual(urls, ["http://x:8008", "http://y:8009"])

    def test_promotion_eligible(self):
        from services.federation_peer_addrbook import promotion_eligible

        book = {
            **default_addrbook(),
            "success_count": 5,
            "score": 0.9,
            "ledger_valid": True,
        }
        self.assertTrue(promotion_eligible(book, ledger_valid=True))
        book["success_count"] = 2
        self.assertFalse(promotion_eligible(book, ledger_valid=True))


class TrustConfigPromoteTests(unittest.TestCase):
    def test_append_trusted_node_to_yaml(self):
        import tempfile
        from pathlib import Path

        from schemas.federation import TrustedNode
        from services.trust_config import append_trusted_node_to_yaml, clear_trusted_nodes_cache, load_trusted_nodes_from_yaml

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trusted_nodes.yaml"
            node = TrustedNode(node_id="peer-x", base_url="http://peer-x:8008", trust_weight=0.8)
            self.assertTrue(append_trusted_node_to_yaml(node, path=path))
            self.assertFalse(append_trusted_node_to_yaml(node, path=path))
            clear_trusted_nodes_cache()
            loaded = load_trusted_nodes_from_yaml(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].node_id, "peer-x")


if __name__ == "__main__":
    unittest.main()
