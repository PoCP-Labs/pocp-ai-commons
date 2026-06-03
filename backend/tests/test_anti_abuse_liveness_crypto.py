"""Security liveness: /health must not block on liboqs during suite auto-detection."""

import os
import unittest
from unittest.mock import patch

from services.crypto_suite import (
    SUITE_V01_CLASSIC,
    SUITE_V02_HYBRID,
    active_crypto_suite,
    clear_active_crypto_suite_cache,
)


class LivenessCryptoSuiteTests(unittest.TestCase):
    def tearDown(self):
        clear_active_crypto_suite_cache()

    @patch.dict(os.environ, {}, clear=True)
    @patch("services.crypto_suite.get_pqc_public_key_hex")
    def test_active_crypto_suite_skips_liboqs_without_pqc_env(self, mock_pqc):
        self.assertEqual(active_crypto_suite(), SUITE_V01_CLASSIC)
        mock_pqc.assert_not_called()

    @patch.dict(
        os.environ,
        {"POCP_NODE_PQC_PUBLIC_KEY": "aa" * 32},
        clear=True,
    )
    @patch("services.crypto_suite.get_pqc_public_key_hex")
    def test_active_crypto_suite_hybrid_from_public_key_env_only(self, mock_pqc):
        clear_active_crypto_suite_cache()
        self.assertEqual(active_crypto_suite(), SUITE_V02_HYBRID)
        mock_pqc.assert_not_called()

    @patch.dict(
        os.environ,
        {"POCP_NODE_PQC_PRIVATE_KEY": os.urandom(32).hex()},
        clear=True,
    )
    @patch("services.crypto_suite.get_pqc_public_key_hex")
    def test_active_crypto_suite_hybrid_for_dev_stub_private_key(self, mock_pqc):
        clear_active_crypto_suite_cache()
        self.assertEqual(active_crypto_suite(), SUITE_V02_HYBRID)
        mock_pqc.assert_not_called()

    @patch.dict(
        os.environ,
        {"POCP_CRYPTO_SUITE": SUITE_V01_CLASSIC},
        clear=True,
    )
    def test_explicit_suite_env_overrides_pqc_keys(self):
        clear_active_crypto_suite_cache()
        with patch.dict(os.environ, {"POCP_NODE_PQC_PUBLIC_KEY": "bb" * 32}, clear=False):
            clear_active_crypto_suite_cache()
            self.assertEqual(active_crypto_suite(), SUITE_V01_CLASSIC)


if __name__ == "__main__":
    unittest.main()
