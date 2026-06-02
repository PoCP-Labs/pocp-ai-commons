# PoCP Neural Commons Target Architecture Patch

This patch upgrades `PoCP-Labs/pocp-ai-commons` to the target architecture:

**PoCP Neural Commons Network** — a protocol-based distributed intelligence and compute network powered by verified contribution, tokenized measurement, and entity reputation.

## Added files

- POCP-NEURAL-COMMONS-NETWORK.md
- TOKEN-MEASUREMENT-LAYER.md
- COMPUTE-INTELLIGENCE-TOKENOMICS.md
- CAPABILITY-REGISTRY-SPEC.md
- COMPUTE-NODE-SPEC.md
- NEURAL-ROUTING-SPEC.md
- SETTLEMENT-LAYER-SPEC.md
- REPUTATION-GOVERNANCE-SPEC.md
- README-NEURAL-COMMONS-REWRITE.md
- PR-PLAN-NEURAL-COMMONS.md
- docs/NEURAL-COMMONS-INTEGRATION-GUIDE.md
- docs/NEURAL-COMMONS-GLOSSARY.md
- .github/ISSUE_TEMPLATE/neural_commons_architecture.md
- .github/ISSUE_TEMPLATE/token_measurement_task.md
- .github/ISSUE_TEMPLATE/capability_registry_task.md
- .github/ISSUE_TEMPLATE/neural_routing_task.md
- .github/ISSUE_TEMPLATE/settlement_layer_task.md
- .github/ISSUE_TEMPLATE/compute_node_task.md
- apply_neural_commons_target_patch.py
- CURSOR_APPLY_PROMPT.md

## Apply

```bash
cd pocp-ai-commons
python /path/to/pocp_neural_commons_target_patch/apply_neural_commons_target_patch.py
```

Then paste `CURSOR_APPLY_PROMPT.md` into Cursor.

## Suggested commit

```bash
git checkout -b neural-commons-target-architecture
git add .
git commit -m "Add PoCP Neural Commons target architecture"
git push origin neural-commons-target-architecture
```
