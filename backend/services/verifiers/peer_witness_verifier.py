"""Remote witness via federated peer compute node (NN-5)."""

from __future__ import annotations

import os

import httpx

from services.peer_compute import PeerComputeNode
from services.verifiers.base import BaseVerifier, VerifierResult
from services.verifiers.openai_verifier import normalize_result


class PeerWitnessVerifier(BaseVerifier):
    """POST verification context to a trusted peer's /intelligence/compute/witness endpoint."""

    def __init__(self, peer: PeerComputeNode):
        self.peer = peer
        self.provider_name = f"peer:{peer.node_id}"
        self.timeout = float(os.getenv("POCP_PEER_WITNESS_TIMEOUT", "90"))

    @property
    def available(self) -> bool:
        return bool(self.peer.base_url)

    async def verify(self, context: dict) -> VerifierResult:
        url = f"{self.peer.base_url.rstrip('/')}{self.peer.witness_path}"
        headers = {"Content-Type": "application/json"}
        from services.peer_trust import build_peer_auth_headers

        headers.update(build_peer_auth_headers(source_node_id=os.getenv("POCP_NODE_ID", "local")))

        payload = {
            "context": context,
            "provider": self.peer.default_provider,
            "source_node_id": os.getenv("POCP_NODE_ID", "local"),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        result_payload = data.get("result") if isinstance(data.get("result"), dict) else data
        if "provider" in result_payload and "quality" in result_payload:
            parsed = VerifierResult.model_validate(result_payload)
            return parsed.model_copy(update={"provider": self.provider_name})
        normalized = normalize_result(
            self.provider_name,
            str(result_payload.get("model") or self.peer.default_provider),
            result_payload,
        )
        return normalized
