# Capability Schema v0.3

Entity-attached capabilities for PoCP settlement. External networks (Akash, Render, io.net, Gensyn) register as **Compute Entities** via [COMPUTE-ADAPTER-SPEC.md](../COMPUTE-ADAPTER-SPEC.md); MCP tools register as **Tool Entities**. PoCP records invocation after upstream transport completes; **internal BC/AIC settlement** flows through the [Exchange Spine](./EXCHANGE-SPINE-v0.1.md) — not external network token transfers.

See also: [TRAINING-CONTRIBUTION-SPEC.md](../TRAINING-CONTRIBUTION-SPEC.md) · [inspiration-mappings/mcp.md](../inspiration-mappings/mcp.md)

---

## Field reference

| Field | Notes |
|-------|--------|
| `capability_type` | PoCP taxonomy — includes compute + training (v0.3) |
| `unit` | Meter for CP advisory — not on-chain price |
| `price_model` | Advisory only; `sponsored` common in Sprint Alpha |
| `accepted_units` | AIC / CC / PT — ledger units, not external network tokens |
| `verification_method` | Witness plugin hint + policy finalization (`policy_delegate` default for Sprint Alpha) |

### `capability_type` (v0.3)

```text
coding | reasoning | review | gpu_inference | tool_call | training | embeddings | witness
```

### `unit` (v0.3)

```text
skill_invocation | agent_run | llm_token | gpu_second | training_epoch | mcp_tool_call
```

---

## Example — Skill / Agent capability

```json
{
  "capability_id": "cap_001",
  "entity_id": "entity_001",
  "capability_type": "coding",
  "name": "Code Review Capability",
  "unit": "skill_invocation",
  "price_model": "sponsored",
  "base_price": 5,
  "accepted_units": ["AIC", "CC"],
  "verification_method": "human_review",
  "availability": "available",
  "reputation_score": 0,
  "risk_level": "low",
  "metadata": {
    "evidence_standard": "pocp.evidence.v0.1"
  }
}
```

---

## Example — MCP Tool Entity

```json
{
  "capability_id": "cap_mcp_filesystem",
  "entity_id": "pocp-tool-mcp-filesystem",
  "capability_type": "tool_call",
  "name": "MCP filesystem read",
  "unit": "mcp_tool_call",
  "price_model": "sponsored",
  "base_price": 1,
  "accepted_units": ["AIC"],
  "verification_method": "log",
  "availability": "available",
  "reputation_score": 0,
  "risk_level": "medium",
  "metadata": {
    "mcp_server": "filesystem",
    "proof_layer": "mcp_invocation_context",
    "transport": "stdio"
  }
}
```

---

## Example — External compute (Akash / Render / io.net)

```json
{
  "capability_id": "cap_akash_infer",
  "entity_id": "pocp-adapt-akash-demo",
  "capability_type": "gpu_inference",
  "name": "Akash GPU inference (adapter)",
  "unit": "gpu_second",
  "price_model": "dynamic",
  "base_price": 0,
  "accepted_units": ["AIC", "CC"],
  "verification_method": "tee",
  "availability": "limited",
  "reputation_score": 0,
  "risk_level": "medium",
  "metadata": {
    "compute_adapter": "akash",
    "adapter_mode": "stub",
    "contribution_bound": true,
    "external_token_settlement": false,
    "receipt_capability": "llm_inference"
  }
}
```

---

## Example — Training contribution (Gensyn-aligned)

Training uses `contribution_type: training` plus a Compute Entity with `capability_type: training`. Settlement requires `integrity.training_attestation` on the ComputeReceipt — not on-chain training market completion.

```json
{
  "capability_id": "cap_gensyn_train",
  "entity_id": "pocp-adapt-gensyn-ui",
  "capability_type": "training",
  "name": "Gensyn training attestation (adapter stub)",
  "unit": "training_epoch",
  "price_model": "sponsored",
  "base_price": 0,
  "accepted_units": ["AIC", "CC"],
  "verification_method": "benchmark",
  "availability": "available",
  "reputation_score": 0,
  "risk_level": "high",
  "metadata": {
    "compute_adapter": "gensyn",
    "adapter_mode": "stub",
    "contribution_type": "training",
    "evidence_standard": "pocp.training_contribution.v0.1",
    "integrity_extensions": ["training_attestation", "verifier_signatures"],
    "finalization": {
      "auto_on_job_complete": false,
      "requires_human_or_policy": true
    }
  }
}
```

Evidence payload shape: `backend/config/schemas/training_contribution_v0.1.yaml`.
