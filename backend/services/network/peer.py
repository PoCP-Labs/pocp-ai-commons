from __future__ import annotations
import uuid
from .types import NetworkPeer

class PeerRegistry:
    def __init__(self) -> None:
        self._peers: dict[str, NetworkPeer] = {}

    def add_peer(self, node_id: str, entity_id: str, roles: list[str],
                 addresses: list[str] | None = None, public_key: str | None = None) -> NetworkPeer:
        peer = NetworkPeer(
            peer_id=f"peer_{uuid.uuid4().hex[:16]}",
            node_id=node_id,
            entity_id=entity_id,
            roles=roles,
            addresses=addresses or [],
            public_key=public_key,
        )
        self._peers[peer.peer_id] = peer
        return peer

    def all_peers(self) -> list[NetworkPeer]:
        return list(self._peers.values())
