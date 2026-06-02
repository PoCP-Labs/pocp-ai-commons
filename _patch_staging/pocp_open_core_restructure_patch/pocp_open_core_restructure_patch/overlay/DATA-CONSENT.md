# Data Consent Policy

## 1. Purpose

PoCP records contribution events involving humans, agents, skills, tools, datasets, workflows, organizations, and compute nodes.

This data may be valuable for verification, reputation, research, routing, and model improvement.

Data use must be explicit and consent-based.

## 2. Data Categories

PoCP may process:

- entity profile data;
- contribution descriptions;
- evidence links;
- invocation logs;
- AI usage logs;
- compute usage logs;
- verification results;
- human review decisions;
- settlement records;
- reputation records;
- graph relationships.

## 3. Consent Levels

Each contribution or data source should support consent levels:

```text
verification_only
search_and_retrieval
anonymized_research
model_improvement
commercial_model_training
no_reuse_beyond_task
```

## 4. Default Rule

Default should be:

```text
verification_only
```

A contribution should not automatically become training data.

## 5. AI Training

Using contribution data for model training requires explicit consent.

Commercial model training requires separate explicit consent.

## 6. Data Minimization

PoCP should store only what is needed for:

- verification;
- review;
- settlement;
- reputation;
- audit;
- user-requested reuse.

## 7. Deletion and Redaction

Where technically and legally feasible, users should be able to request:

- profile redaction;
- evidence removal;
- personal data deletion;
- anonymization;
- consent withdrawal.

Ledger and audit records may need special handling if they are required for integrity.

## 8. Principle

Contribution should be visible and verifiable.

Personal data should not be exploited.

PoCP begins with contribution.
