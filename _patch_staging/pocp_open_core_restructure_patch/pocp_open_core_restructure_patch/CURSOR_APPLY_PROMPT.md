# Cursor Prompt: Apply PoCP Open Core Restructure Patch

You are working in:

`PoCP-Labs/pocp-ai-commons`

A patch has been applied to restructure PoCP's open-source and commercial boundaries.

## Strategic goal

PoCP should follow an **Open Core** model:

```text
Open:
- protocol specifications
- reference implementation
- SDKs
- basic AI Commons platform
- basic contribution ledger
- basic CP / AI Credits / Compute Credits accounting
- basic Entity / Contribution / Reputation / Settlement schemas
- community tools and examples

Commercial / restricted:
- advanced anti-abuse intelligence
- commercial neural routing
- enterprise governance console
- managed compute scheduling
- private deployment tools
- commercial API gateway
- advanced reputation and risk models
```

## Tasks

### 1. Add documentation links to README

Add a section:

```markdown
## Open Core Strategy

PoCP follows an Open Core model.

The protocol specifications, reference implementation, SDKs, and community tools are open source.

Advanced anti-abuse intelligence, commercial neural routing, enterprise governance, managed compute scheduling, commercial API gateway, private deployment tooling, and advanced reputation / risk models may be provided under separate commercial terms.

See:

- [Open Core Strategy](OPEN-CORE.md)
- [License Policy](LICENSE-POLICY.md)
- [Commercial Boundary](COMMERCIAL.md)
- [Security Policy](SECURITY.md)
- [Data Consent](DATA-CONSENT.md)
- [Anti-Abuse Policy](ANTI-ABUSE-POLICY.md)
- [Repository Boundary](REPOSITORY-BOUNDARY.md)
- [Open Source Roadmap](OPEN-SOURCE-ROADMAP.md)
- [Commercial Modules](COMMERCIAL-MODULES.md)
```

### 2. Preserve existing README content

Do not remove quick start, API, demo, smoke test, or current PoCP AI Commons / Neural Commons positioning.

### 3. Do not change license automatically

Do not change MIT to Apache-2.0 in code yet unless explicitly requested.

Instead, add `LICENSE-POLICY.md` explaining recommended future move to Apache-2.0 for core code and CC BY 4.0 for protocol docs.

### 4. Add issue templates

Preserve existing issue templates and add the new Open Core templates.

### 5. Add repository split roadmap

Use `REPOSITORY-BOUNDARY.md` as the policy for future repo organization.

### 6. Do not expose sensitive implementation details

Do not open-source advanced anti-abuse parameters, risk model internals, commercial routing algorithms, compute scheduler optimization rules, or enterprise private deployment secrets.

### 7. Suggested commit

```text
Add Open Core strategy and repository boundary policy
```

## After this PR

Recommended next PRs:

1. Format backend Python source files.
2. Add `SECURITY.md` reporting process to GitHub Security.
3. Create future `pocp-protocol-spec` repo.
4. Create future SDK repos.
5. Move commercial module planning into private repositories.
