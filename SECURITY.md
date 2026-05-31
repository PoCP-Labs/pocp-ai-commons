# Security Policy

## 1. Security Scope

PoCP security covers:

- contribution event integrity;
- wallet and credit accounting;
- CP / AI Credits / Compute Credits transactions;
- verification records;
- human review integrity;
- settlement records;
- reputation updates;
- API access;
- abuse prevention;
- data consent;
- private deployment security.

## 2. Reporting Vulnerabilities

If you discover a vulnerability, please do not open a public issue with exploit details.

Instead, contact the maintainers privately.

Suggested contact:

```text
security@pocp.network
```

If no dedicated email is available, use the GitHub organization contact or open a private security advisory if enabled.

## 3. Vulnerability Types

Please report:

- authentication bypass;
- credit balance manipulation;
- unauthorized wallet changes;
- ledger tampering;
- replay attacks;
- self-approval bypass;
- verifier manipulation;
- settlement manipulation;
- reputation manipulation;
- data exposure;
- secret leakage;
- dependency vulnerabilities;
- denial-of-service vectors.

## 4. Public vs Private Security Work

Open-source:

- security principles;
- basic validation;
- secure coding practices;
- public test cases;
- responsible disclosure policy.

Restricted:

- advanced anti-abuse parameters;
- private abuse signatures;
- risk model weights;
- fraud graph logic;
- blacklists;
- commercial monitoring rules.

## 5. Minimum Security Requirements

Every contribution-related API should protect:

- who can submit;
- who can verify;
- who can review;
- who can approve;
- who can receive rewards;
- who can spend credits;
- who can modify ledger records;
- who can update reputation.

## 6. Principle

Transparency builds trust.

But not every defensive detail should be exposed to attackers.

PoCP begins with contribution.
