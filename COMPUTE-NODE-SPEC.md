# Compute Node Spec

## Purpose

Compute Nodes are entities that provide compute capability to the PoCP Neural Commons Network.

They may provide GPU inference, GPU training, CPU processing, storage, bandwidth, model serving, vector search, verification computation, and agent runtime.

## Compute Node Entity

Compute Node should be an Entity type.

```text
EntityType.compute_node
```

## Compute Node Profile

Suggested fields:

```json
{
  "entity_id": "compute_001",
  "node_name": "A100 Node Tokyo 01",
  "owner_entity_id": "org_001",
  "hardware": {
    "gpu_type": "A100",
    "gpu_count": 4,
    "vram_gb": 320,
    "cpu": "EPYC",
    "memory_gb": 512,
    "storage_gb": 4000
  },
  "capabilities": [
    "gpu_inference",
    "gpu_training",
    "model_serving"
  ],
  "region": "ap-northeast",
  "availability": "available",
  "pricing": {
    "unit": "gpu_second",
    "base_price": 0.01,
    "accepted_units": ["CC", "PT"]
  },
  "verification_methods": ["log", "benchmark", "redundant_execution"],
  "reputation": {
    "uptime": 0.99,
    "success_rate": 0.98
  }
}
```

## Compute Usage

Every compute invocation should record task id, caller entity, compute node, capability id, start time, end time, resource usage, logs, input hash, output hash, verification result, cost, and settlement status.

## Compute Verification

MVP methods:

- execution log;
- output hash;
- requester confirmation;
- benchmark;
- random recomputation;
- redundant node comparison.

Future methods:

- TEE;
- ZK;
- proof of inference;
- proof of training;
- challenge-response.

## Compute Node Rewards

Rewards may include Compute Credits, PoCP internal token units, reputation, priority routing, lower staking requirement, and governance eligibility.

## Compute Node Penalties

Penalties may include reputation reduction, reward withholding, stake slashing, temporary suspension, and removal from routing.

## Principle

Compute Node contribution must be measurable and verifiable.

PoCP begins with contribution.
