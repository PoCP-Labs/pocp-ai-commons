# Compute Node Schema v0.3

```json
{
  "entity_id": "compute_001",
  "entity_type": "compute_node",
  "hardware": {
    "gpu_type": "A100",
    "gpu_count": 4,
    "vram_gb": 320,
    "cpu": "EPYC",
    "memory_gb": 512,
    "storage_gb": 4000
  },
  "region": "ap-northeast",
  "capabilities": ["gpu_inference", "gpu_training", "model_serving"],
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
