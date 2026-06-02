# Node Runtime Spec

NodeProfile defines how an Entity connects to the PoCP network.

## Node Types

```text
light
service
compute
verifier
reviewer
relay
indexer
governance
treasury
```

## Minimal Schema

```json
{
  "node_id": "node_001",
  "entity_id": "skill_001",
  "node_type": "service",
  "did": "did:pocp:skill_001",
  "public_key": "ed25519:...",
  "base_url": "https://skill.example.com",
  "p2p_address": "/ip4/1.2.3.4/tcp/4001/p2p/xxx",
  "health_url": "https://skill.example.com/pocp/health",
  "status": "active",
  "protocol_version": "pocp-node-v0.1"
}
```
