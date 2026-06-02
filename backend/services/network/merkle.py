from __future__ import annotations

from services.merkle_canonical import (
    MERKLE_ALGORITHM,
    build_inclusion_bundle_unified,
    merkle_root_unified,
    merkle_root_unified_display,
)


class MerkleService:
    """ProtocolEvent batch Merkle — delegates to ledger-compatible sha256-pair-concat-v0.1."""

    algorithm = MERKLE_ALGORITHM

    def merkle_root(self, hashes: list[str]) -> str:
        """Display root with sha256: prefix (protocol event convention)."""
        return merkle_root_unified_display(hashes)

    def merkle_root_hex(self, hashes: list[str]) -> str:
        """Bare hex root — matches ledger_merkle_inclusion."""
        return merkle_root_unified(hashes)

    def inclusion_bundle(self, hashes: list[str], target_hash: str) -> dict | None:
        return build_inclusion_bundle_unified(hashes, target_hash)
