# Migration from AI Commons to Capability Internet Protocol

## Current State

```text
Entity registers
→ receives starter AI Credits
→ submits contribution
→ AI advisory verify
→ human approve
→ CP + AI Credits issued
→ ledger written
```

## Target State

```text
Entity
→ NodeProfile
→ PublicNodeEndpoint
→ Capability
→ Invocation
→ Proof
→ Verification
→ Settlement
→ TokenAccount
→ ReputationGraph
→ ProtocolEvent
```

## Mapping

```text
ContributionEvent       → Proof / Contribution Proof
AI Verification         → VerificationRecord
Human Review            → Reviewer Decision
CreditTransaction       → SettlementParticipant + TokenAccount transaction
LedgerRecord            → ProtocolEvent
ReputationScore         → ReputationRecord scoped by capability
```

## Rule

Do not delete the Genesis Loop.

Wrap and extend it.
