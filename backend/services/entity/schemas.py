"""Frozen Entity layer catalog contract (CI-1).

Aligned with:
- docs/protocol/ENTITY-LAYER-SPEC.md
- intelligence/entity_ontology.py
- services/capability/seeds.py (stable IDs — do not drift)
"""

from __future__ import annotations

ENTITY_ONTOLOGY_SPEC_VERSION = "0.3"
ENTITY_TYPE_COUNT = 14
REGISTRY_MIN_CAPABILITY_COUNT = 11

# Stable infrastructure entity IDs seeded by ensure_platform_entity_catalog().
LOCAL_COMPUTE_NODE_ID = "pocp-entity-local-compute"
LOCAL_VERIFIER_NODE_ID = "pocp-entity-local-verifier"
BOB_REVIEWER_NODE_ID = "pocp-entity-bob-reviewer"
RAIN_SPONSOR_ID = "pocp-entity-rain-sponsor"
PROTOCOL_TREASURY_ID = "pocp-entity-protocol-treasury"
STUDY_WORKFLOW_ID = "pocp-entity-study-workflow"

INFRASTRUCTURE_ENTITY_IDS = frozenset(
    {
        LOCAL_COMPUTE_NODE_ID,
        LOCAL_VERIFIER_NODE_ID,
        BOB_REVIEWER_NODE_ID,
        RAIN_SPONSOR_ID,
        PROTOCOL_TREASURY_ID,
        STUDY_WORKFLOW_ID,
    }
)

# Infrastructure entities that receive NodeProfile rows on catalog repair (CI-1 → CI-2).
# Excludes STUDY_WORKFLOW_ID (Entity-only workflow; no public node surface).
NODE_ELIGIBLE_INFRASTRUCTURE_IDS = frozenset(
    {
        LOCAL_COMPUTE_NODE_ID,
        LOCAL_VERIFIER_NODE_ID,
        BOB_REVIEWER_NODE_ID,
        RAIN_SPONSOR_ID,
        PROTOCOL_TREASURY_ID,
    }
)

# Mirror of capability.seeds infrastructure IDs — Forge MUST keep seeds.py in sync.
INFRASTRUCTURE_ID_TUPLE = tuple(sorted(INFRASTRUCTURE_ENTITY_IDS))
