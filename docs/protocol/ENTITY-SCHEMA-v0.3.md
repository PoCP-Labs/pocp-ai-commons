# Entity Schema v0.3

```json
{
  "entity_id": "entity_001",
  "entity_type": "human | agent | llm | skill | tool | dataset | workflow | compute_node | verifier_node | reviewer_node | organization | community | sponsor | protocol_treasury",
  "name": "Example Entity",
  "owner_entity_id": null,
  "status": "active | suspended | archived",
  "capabilities": [],
  "wallet_id": "wallet_001",
  "reputation": {},
  "risk_level": "low | medium | high",
  "metadata": {}
}
```

## Connection profile (protocol layer)

Every entity exposes a **connection slice** via ontology / connections APIs:

```json
{
  "connections": {
    "schema": "pocp.entity_connection.v0.1",
    "can_own_types": ["agent", "skill"],
    "typical_invocation_targets": ["agent", "skill"],
    "suggested_invocation_actions": { "agent": "uses" },
    "typical_participant_roles": ["creator", "reviewer"],
    "connect_via": ["registration", "ownership", "contribution_participant", "invocation_trace"]
  }
}
```

See [ENTITY-CONNECTION.md](./ENTITY-CONNECTION.md) for the three-layer model (structural · protocol · operational).
