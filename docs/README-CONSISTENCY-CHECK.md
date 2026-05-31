# README Consistency Check

## Purpose

README must match the actual repository state.

If README describes target architecture, it must clearly say so.

## Checklist

- [ ] README title matches current positioning.
- [ ] README explains current working demo.
- [ ] README links only to existing files.
- [ ] Target architecture is marked as target architecture.
- [ ] Current implementation is marked as reference implementation.
- [ ] API examples match current routes.
- [ ] Quick Start works or limitations are documented.
- [ ] README mentions public-core vs commercial-reserved boundary.
- [ ] README avoids promising public token issuance.
- [ ] README preserves AI advisory / human final principle.

## Suggested Wording

```markdown
Some architecture documents describe the target modular structure. The current reference implementation may still use aggregated routers or services while modularization is in progress.
```

## Link Check

Run:

```bash
python backend/scripts/health_check.py
```

Then manually verify important README links.

PoCP begins with contribution.
