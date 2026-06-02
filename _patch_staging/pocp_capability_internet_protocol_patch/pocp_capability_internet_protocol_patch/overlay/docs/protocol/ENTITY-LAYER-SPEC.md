# Entity Layer Spec

Entity is the foundational network subject of PoCP.

Entity is not UserAccount.

## Entity Types

```text
human
agent
llm
skill
tool
dataset
workflow
compute_node
verifier_node
reviewer_node
organization
community
sponsor
protocol_treasury
relay_node
indexer_node
governance_node
```

## Rules

- Entity owns TokenAccount.
- Entity owns reputation.
- Entity may own one or more NodeProfiles.
- Entity may publish one or more Capabilities.
- Entity may participate in Settlement.
