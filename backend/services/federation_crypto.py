"""Ed25519 signing for federated contribution proofs and import payloads."""

import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _private_key() -> Ed25519PrivateKey | None:
    raw = os.getenv("POCP_NODE_PRIVATE_KEY", "").strip()
    if not raw:
        return None
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(raw))
    except ValueError:
        return None


def get_node_public_key_hex() -> str | None:
    env_pub = os.getenv("POCP_NODE_PUBLIC_KEY", "").strip()
    if env_pub:
        return env_pub
    key = _private_key()
    if key is None:
        return None
    return key.public_key().public_bytes_raw().hex()


def sign_message(message: str) -> str | None:
    key = _private_key()
    if key is None:
        return None
    return key.sign(message.encode("utf-8")).hex()


def verify_message(message: str, signature_hex: str, public_key_hex: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), message.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError):
        return False


def import_payload_message(
    *,
    source_node_id: str,
    contribution_id: str,
    primary_entity_portable_id: str,
    evidence_hash: str,
    ledger_record_hash: str | None,
) -> str:
    return "|".join(
        [
            source_node_id,
            contribution_id,
            primary_entity_portable_id,
            evidence_hash,
            ledger_record_hash or "",
        ]
    )
