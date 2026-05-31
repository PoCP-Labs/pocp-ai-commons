# Repository Health Checklist

Use this checklist before inviting external contributors.

## Code Quality

- [ ] Python files are readable and not compressed into one-line files.
- [ ] Formatting tool is configured.
- [ ] Linting tool is configured.
- [ ] Backend starts locally.
- [ ] Smoke test runs.
- [ ] Docker Compose works or documented limitations exist.
- [ ] No secrets are committed.
- [ ] No private keys are committed.
- [ ] No commercial risk model internals are committed.

## Documentation

- [ ] README explains project purpose.
- [ ] README has Quick Start.
- [ ] README links to protocol docs.
- [ ] README explains public-core vs commercial-reserved boundary.
- [ ] Architecture docs match actual implementation or clearly say target architecture.
- [ ] CONTRIBUTING exists.
- [ ] SECURITY exists.
- [ ] License policy exists.
- [ ] Data consent policy exists.

## Open Source Process

- [ ] Issue templates exist.
- [ ] PR template exists.
- [ ] Good first contributions exist.
- [ ] Maintainer review process is clear.
- [ ] Human final review principle is clear.
- [ ] No token reward promise is made.

## API / Demo

- [ ] Health endpoint works.
- [ ] Seed data exists.
- [ ] Contribution submit works.
- [ ] AI advisory verification reference flow works.
- [ ] Human approval reference flow works.
- [ ] Ledger records are created.
- [ ] Wallet balances are visible.

## Boundary

- [ ] Public core modules are marked basic/reference/mock where needed.
- [ ] Commercial-reserved modules are not included.
- [ ] Advanced anti-abuse internals are not exposed.
- [ ] Commercial routing internals are not exposed.
- [ ] Compute scheduler internals are not exposed.

PoCP begins with contribution.
