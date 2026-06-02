---
name: Protocol Upgrade Task (PR track)
about: PR-01..PR-15 capability internet upgrade — see UPGRADE-ROADMAP-PR-PLAN.md
title: "[Protocol] "
labels: "protocol, capability-internet"
assignees: ""
---

## PR track

<!-- e.g. PR-05 NodeProfile + PublicNodeEndpoint -->

Link: [docs/UPGRADE-ROADMAP-PR-PLAN.md](../../docs/UPGRADE-ROADMAP-PR-PLAN.md)

## Layer

- [ ] Entity / Node (PR-04, PR-05)
- [ ] Capability (PR-06)
- [ ] Invocation (PR-07)
- [ ] Proof / Verification (PR-08)
- [ ] Settlement (PR-09)
- [ ] Economy / Graph / Events (PR-10..PR-12)
- [ ] Minimum living network (PR-13)

## Meta Agent

<!-- Atlas-0, Pulse-0, Vault-0, Forge-0, Prism-0, Gauge-0 -->

## Acceptance

```powershell
python backend/scripts/smoke_test.py
python -m pytest backend/tests -q -k "<relevant>"
```

## Notes

Genesis Loop APIs must remain working; new protocol objects wrap — do not delete contribution path.
