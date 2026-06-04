"""Minimal PoCP Node Python SDK — connect, quote, invoke, verify_proof via /pocp/* + federation.

CIP-P4.1: product-UI-free client for public node wire and entity dialogue.
Uses stdlib urllib (same pattern as ``services.federation_peers``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA

POCP_PUBLIC_HANDSHAKE_SCHEMA = "pocp.public_node_handshake.v0.1"


class PocpNodeError(RuntimeError):
    """HTTP or transport failure talking to a PoCP node."""

    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class PocpNodeClient:
    """HTTP client for Phase A public node surfaces (``/pocp/*``)."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        local_node_id: str | None = None,
        transport: Any | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.local_node_id = local_node_id or "pocp-sdk-client"
        self._transport = transport
        self._endpoints: dict[str, str] = {}

    def _urlopen(self, request: urllib.request.Request):
        if self._transport is not None:
            return self._transport.open(request)
        return urllib.request.urlopen(request, timeout=self.timeout)

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            params = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
            url = f"{url}?{params}"
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._urlopen(request) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return {}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {"data": parsed}
        except urllib.error.HTTPError as exc:
            detail: Any = None
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except Exception:
                detail = exc.read().decode("utf-8", errors="replace")
            raise PocpNodeError(
                f"{method} {path} failed: HTTP {exc.code}",
                status=exc.code,
                body=detail,
            ) from exc
        except urllib.error.URLError as exc:
            raise PocpNodeError(f"{method} {path} failed: {exc.reason}") from exc

    def _get(self, path: str, *, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, query=query)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, body=body)

    def _pocp_path(self, key: str, fallback: str) -> str:
        endpoint = self._endpoints.get(key)
        if endpoint and endpoint.startswith(self.base_url):
            return endpoint[len(self.base_url) :]
        return fallback

    def refresh_manifest(self) -> dict[str, Any]:
        """Load ``GET /pocp/node`` and cache endpoint map."""
        manifest = self._get("/pocp/node")
        self._endpoints = dict(manifest.get("endpoints") or {})
        return manifest

    def health(self) -> dict[str, Any]:
        return self._get(self._pocp_path("pocp_health", "/pocp/health"))

    def capabilities(
        self,
        *,
        capability_type: str | None = None,
        exchange_kind: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        return self._get(
            self._pocp_path("pocp_capabilities", "/pocp/capabilities"),
            query={
                "capability_type": capability_type,
                "exchange_kind": exchange_kind,
                "limit": limit,
            },
        )

    def protocol_surface(self) -> dict[str, Any]:
        return self._get("/pocp/protocol")

    def sync(self, *, run: bool = False) -> dict[str, Any]:
        return self._get("/pocp/sync", query={"run": "true" if run else None})

    def connect(
        self,
        peer_base_url: str,
        *,
        capability_type: str | None = None,
        require_trust_bundle_match: bool = False,
    ) -> dict[str, Any]:
        """
        Federation connect via ``POST /pocp/handshake`` on this node.

        When ``base_url`` is the remote peer itself, probes ``/pocp/health`` and
        ``/pocp/node`` directly (no orchestrator handshake).
        """
        peer = peer_base_url.rstrip("/")
        if peer == self.base_url:
            return {
                "schema": "pocp.sdk_peer_connect.v0.1",
                "ok": True,
                "peer_base_url": peer,
                "health": self.health(),
                "manifest": self.refresh_manifest(),
            }
        if peer != self.base_url:
            try:
                remote = PocpNodeClient(peer, timeout=self.timeout)
                health = remote.health()
                manifest = remote.refresh_manifest()
                return {
                    "schema": "pocp.sdk_peer_connect.v0.1",
                    "ok": True,
                    "peer_base_url": peer,
                    "health": health,
                    "manifest": manifest,
                }
            except PocpNodeError:
                pass
        body: dict[str, Any] = {
            "peer_base_url": peer,
            "require_trust_bundle_match": require_trust_bundle_match,
        }
        if capability_type:
            body["capability_type"] = capability_type
        return self._post(self._pocp_path("pocp_handshake", "/pocp/handshake"), body)

    @staticmethod
    def dialogue_envelope(
        *,
        kind: str,
        dialogue_id: str | None = None,
        from_ref: dict[str, Any],
        to_ref: dict[str, Any],
        payload: dict[str, Any] | None = None,
        refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        envelope: dict[str, Any] = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": dialogue_id or f"dlg_{uuid.uuid4().hex[:12]}",
            "kind": kind,
            "from": from_ref,
            "to": to_ref,
            "payload": payload or {},
        }
        if refs:
            envelope["refs"] = refs
        return envelope

    def quote(
        self,
        *,
        from_ref: dict[str, Any],
        to_ref: dict[str, Any],
        payload: dict[str, Any] | None = None,
        dialogue_id: str | None = None,
        refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Pre-invoke exchange quote via ``POST /pocp/invoke`` (kind=quote)."""
        envelope = self.dialogue_envelope(
            kind="quote",
            dialogue_id=dialogue_id,
            from_ref=from_ref,
            to_ref=to_ref,
            payload=payload,
            refs=refs,
        )
        return self.invoke(envelope)

    def invoke(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Entity dialogue invoke via ``POST /pocp/invoke``."""
        schema = envelope.get("schema")
        if schema and schema != ENTITY_DIALOGUE_SCHEMA:
            raise ValueError(f"schema must be {ENTITY_DIALOGUE_SCHEMA}")
        return self._post(self._pocp_path("pocp_invoke", "/pocp/invoke"), envelope)

    def ping(
        self,
        *,
        entity_id: str = "local",
        node_id: str | None = None,
    ) -> dict[str, Any]:
        node = node_id or self.local_node_id
        ref = {"entity_id": entity_id, "node_id": node}
        return self.invoke(
            self.dialogue_envelope(kind="ping", from_ref=ref, to_ref=ref, payload={}),
        )

    def verify_proof(
        self,
        proof: dict[str, Any],
        *,
        trusted_public_key: str | None = None,
        require_signature: bool = False,
    ) -> dict[str, Any]:
        """Offline proof verify via ``POST /pocp/proofs``."""
        body: dict[str, Any] = {"proof": proof, "require_signature": require_signature}
        if trusted_public_key:
            body["trusted_public_key"] = trusted_public_key
        return self._post(self._pocp_path("pocp_proofs", "/pocp/proofs"), body)
