# PoCP Network Architecture

## 12-Layer Architecture

```text
PoCP Neural Commons Network
│
├── 1. Entity Layer
├── 2. Node Layer
├── 3. Identity Layer
├── 4. Capability Layer
├── 5. Discovery Layer
├── 6. Invocation Layer
├── 7. Proof Layer
├── 8. Verification Layer
├── 9. Settlement Layer
├── 10. Reputation Graph Layer
├── 11. Governance Layer
└── 12. Protocol Economy Layer
```

## No Central Platform Requirement

PoCP does not require one central platform server.

It requires many protocol nodes:

```text
Entity Nodes
Bootstrap Nodes
Relay Nodes
Verifier Nodes
Reviewer Nodes
Indexer Nodes
Storage Nodes
Settlement Nodes
Governance Nodes
Compute Nodes
Capability Nodes
```

These nodes do not control PoCP individually.

They execute the protocol.

## Design Rule

Architecture should be decentralized by design, even when early reference implementations use a local server or SQLite.
