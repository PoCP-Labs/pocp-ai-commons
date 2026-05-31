"""Optional ML-DSA-65 (FIPS 204) via liboqs-python; dev stub fallback."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

PQC_SIG_TARGET = "ml-dsa-65"
PQC_SIG_DEV_STUB = "ml-dsa-dev-stub-v0"

_LIBOQS_AVAILABLE = False
_LIBOQS_SIG_NAME: str | None = None

try:
    import oqs  # type: ignore[import-untyped]

    _enabled = getattr(oqs, "OQS_ENABLE_SIG", None)
    for _candidate in ("ML-DSA-65", "ML-DSA-87", "Dilithium3"):
        if _candidate in oqs.get_enabled_sig_mechanisms():
            _LIBOQS_SIG_NAME = _candidate
            _LIBOQS_AVAILABLE = True
            break
except ImportError:
    pass


def liboqs_available() -> bool:
    return _LIBOQS_AVAILABLE and _LIBOQS_SIG_NAME is not None


def liboqs_mechanism() -> str | None:
    return _LIBOQS_SIG_NAME


def _pqc_private_key_bytes() -> bytes | None:
    raw = os.getenv("POCP_NODE_PQC_PRIVATE_KEY", "").strip()
    if not raw:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def get_pqc_public_key_hex() -> str | None:
    env_pub = os.getenv("POCP_NODE_PQC_PUBLIC_KEY", "").strip()
    if env_pub:
        return env_pub
    if liboqs_available():
        key = _pqc_private_key_bytes()
        if key is None:
            return None
        try:
            with oqs.Signature(_LIBOQS_SIG_NAME) as signer:  # type: ignore[name-defined]
                return signer.export_public_key().hex()
        except Exception:
            return None
    key = _pqc_private_key_bytes()
    if key is None:
        return None
    return hashlib.sha256(key).hexdigest()


def _is_liboqs_secret_key(key: bytes) -> bool:
    """ML-DSA secret keys are much larger than the 32-byte dev stub."""
    return len(key) >= 256


def _dev_stub_public_key(private_key: bytes) -> str:
    return hashlib.sha256(private_key).hexdigest()


def _dev_stub_sign(public_key_hex: str, message: str) -> str:
    """Public-key verifiable dev stub — peers verify with trusted pqc_public_key only."""
    return hmac.new(public_key_hex.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_pqc(message: str) -> tuple[str, str, str] | None:
    """Return (algorithm, public_key_hex, signature_hex) or None."""
    key = _pqc_private_key_bytes()
    if key is None:
        return None

    if liboqs_available() and _is_liboqs_secret_key(key):
        try:
            with oqs.Signature(_LIBOQS_SIG_NAME) as signer:  # type: ignore[name-defined]
                signer.import_secret_key(key)
                signature = signer.sign(message.encode("utf-8")).hex()
                public_key = signer.export_public_key().hex()
                return PQC_SIG_TARGET, public_key, signature
        except Exception:
            pass

    public_key = _dev_stub_public_key(key)
    signature = _dev_stub_sign(public_key, message)
    return PQC_SIG_DEV_STUB, public_key, signature


def verify_pqc(
    message: str,
    algorithm: str,
    public_key_hex: str,
    signature_hex: str,
) -> bool:
    if algorithm == PQC_SIG_TARGET and liboqs_available():
        try:
            with oqs.Signature(_LIBOQS_SIG_NAME) as verifier:  # type: ignore[name-defined]
                public_key = bytes.fromhex(public_key_hex)
                verifier.import_public_key(public_key)
                return verifier.verify(message.encode("utf-8"), bytes.fromhex(signature_hex))
        except Exception:
            return False

    if algorithm == PQC_SIG_DEV_STUB or (algorithm == PQC_SIG_TARGET and not liboqs_available()):
        if _dev_stub_sign(public_key_hex, message) == signature_hex:
            return True
        key = _pqc_private_key_bytes()
        if key is None:
            return False
        expected_pub = _dev_stub_public_key(key)
        if public_key_hex != expected_pub:
            return False
        legacy_sig = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(legacy_sig, signature_hex)

    return False


def pqc_implementation_status() -> dict[str, Any]:
    return {
        "liboqs_available": liboqs_available(),
        "liboqs_mechanism": liboqs_mechanism(),
        "fallback_stub": PQC_SIG_DEV_STUB,
        "production_target": PQC_SIG_TARGET,
    }
