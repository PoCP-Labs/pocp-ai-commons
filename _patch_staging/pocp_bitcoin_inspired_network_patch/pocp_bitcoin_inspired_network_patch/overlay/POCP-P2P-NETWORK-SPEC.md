# PoCP P2P Network Spec

## Purpose

PoCP should support a network of Entity Nodes rather than relying on one central platform server.

## Node Types

```text
Human Light Node
Agent Node
Skill Node
Tool Node
Dataset Node
Workflow Node
Compute Node
Verifier Node
Reviewer Node
Indexer Node
Relay Node
Full Event Node
Governance Node
```

## Network Responsibilities

```text
peer discovery
event broadcast
pending event propagation
event validation
batch synchronization
light node support
relay / NAT traversal
reputation index synchronization
```

## Event Broadcast

Nodes broadcast signed ProtocolEvents:

```text
NodeRegistered
CapabilityPublished
InvocationCreated
ProofSubmitted
VerificationCompleted
SettlementExecuted
ReputationUpdated
```
