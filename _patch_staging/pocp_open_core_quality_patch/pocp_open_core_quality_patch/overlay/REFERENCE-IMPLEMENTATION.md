# Reference Implementation

## Purpose

`pocp-ai-commons` is the public reference implementation for the PoCP protocol family.

It is not required to contain every future commercial capability.

It should demonstrate the minimum trustworthy loop:

```text
Entity
→ Task
→ Contribution
→ AI Advisory Verification
→ Human Review
→ CP / AI Credits
→ Ledger
→ Reputation / Graph
```

## What the Reference Implementation Should Include

The public reference implementation should include:

- Entity registry basics;
- Contribution event basics;
- Wallet and credit accounting basics;
- AI verifier reference implementation;
- Human review reference implementation;
- Basic reward distribution;
- Ledger records;
- Basic reputation updates;
- Basic graph;
- seed data;
- smoke test;
- developer docs.

## What It Should Not Include

The public reference implementation should not include:

- advanced anti-abuse intelligence;
- private risk model weights;
- commercial neural routing algorithms;
- managed compute scheduler;
- enterprise governance console;
- enterprise API gateway;
- private deployment secrets;
- commercial settlement parameters.

## Reference vs Production

This repository may include code that is intentionally simple.

Such code should be clearly marked as:

```text
reference
basic
mock
example
adapter
```

Production-grade commercial modules may live separately.

## Naming Convention

Recommended naming for public code:

```text
basic_*
mock_*
reference_*
example_*
adapter_*
```

Avoid adding public files named:

```text
advanced_*
commercial_*
private_*
risk_weights_*
enterprise_*
```

unless they only contain interfaces or documentation.

## Principle

A reference implementation should be clear enough to learn from and safe enough to build upon.

PoCP begins with contribution.
